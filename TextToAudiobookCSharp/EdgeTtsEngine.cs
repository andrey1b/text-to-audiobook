using System.IO;
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;

namespace TextToAudiobookCSharp;

/// <summary>
/// Движок синтеза речи через Microsoft Edge TTS (WebSocket API).
/// Бесплатный, не требует ключей API.
/// </summary>
public class EdgeTtsEngine
{
    private const string TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
    private const string VOICE_LIST_URL =
        $"https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclienttoken={TRUSTED_CLIENT_TOKEN}";

    public int MaxRetries { get; set; } = 5;
    public int[] RetryDelays { get; set; } = [5, 15, 30, 60, 120];

    private static string MakeTimestamp()
    {
        // Формат как в edge-tts Python: "Thu Oct 09 2024 07:23:42 GMT+0000 (Coordinated Universal Time)"
        var now = DateTimeOffset.UtcNow;
        return now.ToString("ddd MMM dd yyyy HH:mm:ss",
            System.Globalization.CultureInfo.InvariantCulture) +
            " GMT+0000 (Coordinated Universal Time)";
    }

    private static string MakeWssUrl()
    {
        string connectionId = Guid.NewGuid().ToString("N");
        return $"wss://speech.platform.bing.com/consumer/speech/synthesize/" +
               $"readaloud/edge/v1?TrustedClientToken={TRUSTED_CLIENT_TOKEN}" +
               $"&ConnectionId={connectionId}";
    }

    public async Task SynthesizeAsync(
        string text, string voice, string speed, string outputPath,
        Action<string>? log = null, CancellationToken ct = default)
    {
        for (int attempt = 0; attempt <= MaxRetries; attempt++)
        {
            try
            {
                await SynthesizeInternalAsync(text, voice, speed, outputPath, ct);
                return;
            }
            catch (Exception ex) when (attempt < MaxRetries && !ct.IsCancellationRequested)
            {
                int delay = RetryDelays[Math.Min(attempt, RetryDelays.Length - 1)];
                log?.Invoke($"  Сервер недоступен: {ex.Message}");
                log?.Invoke($"  Повторная попытка через {delay} сек ({attempt + 1}/{MaxRetries})...");
                await Task.Delay(delay * 1000, ct);
            }
        }
    }

    private static async Task SynthesizeInternalAsync(
        string text, string voice, string speed, string outputPath, CancellationToken ct)
    {
        using var ws = new ClientWebSocket();
        ws.Options.SetRequestHeader("User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0");
        ws.Options.SetRequestHeader("Pragma", "no-cache");
        ws.Options.SetRequestHeader("Cache-Control", "no-cache");
        ws.Options.SetRequestHeader("Origin", "chrome-extension://jdiccldimpdaibmpdmdber");

        string url = MakeWssUrl();
        await ws.ConnectAsync(new Uri(url), ct);

        string requestId = Guid.NewGuid().ToString("N");
        string ts = MakeTimestamp();

        // 1. Отправляем speech.config
        string configMsg =
            $"X-Timestamp:{ts}\r\n" +
            "Content-Type:application/json; charset=utf-8\r\n" +
            "Path:speech.config\r\n\r\n" +
            "{\"context\":{\"synthesis\":{\"audio\":{" +
            "\"metadataoptions\":{" +
            "\"sentenceBoundaryEnabled\":\"false\"," +
            "\"wordBoundaryEnabled\":\"false\"}," +
            "\"outputFormat\":\"audio-24khz-48kbitrate-mono-mp3\"" +
            "}}}}";

        await SendTextAsync(ws, configMsg, ct);

        // 2. Отправляем SSML
        string escapedText = System.Security.SecurityElement.Escape(text);
        string ssml =
            "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>" +
            $"<voice name='{voice}'>" +
            $"<prosody pitch='+0Hz' rate='{speed}' volume='+0%'>" +
            escapedText +
            "</prosody></voice></speak>";

        string ssmlMsg =
            $"X-RequestId:{requestId}\r\n" +
            "Content-Type:application/ssml+xml\r\n" +
            $"X-Timestamp:{ts}\r\n" +
            "Path:ssml\r\n\r\n" + ssml;

        await SendTextAsync(ws, ssmlMsg, ct);

        // 3. Читаем ответ — собираем MP3
        using var audioStream = new MemoryStream();
        var buffer = new byte[65536]; // 64KB буфер
        bool done = false;

        while (!done)
        {
            ct.ThrowIfCancellationRequested();

            WebSocketReceiveResult result;
            using var msgStream = new MemoryStream();

            // Собираем полное сообщение (может прийти частями)
            do
            {
                result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), ct);
                msgStream.Write(buffer, 0, result.Count);
            } while (!result.EndOfMessage);

            byte[] msgData = msgStream.ToArray();

            if (result.MessageType == WebSocketMessageType.Close)
            {
                done = true;
                break;
            }

            if (result.MessageType == WebSocketMessageType.Binary && msgData.Length > 2)
            {
                // Бинарное сообщение: 2 байта размер заголовка, затем заголовок, затем аудио
                int headerLen = (msgData[0] << 8) | msgData[1];
                int audioStart = 2 + headerLen;

                // Проверяем что это аудио-данные
                if (audioStart < msgData.Length)
                {
                    string header = Encoding.UTF8.GetString(msgData, 2, headerLen);
                    if (header.Contains("Path:audio"))
                    {
                        audioStream.Write(msgData, audioStart, msgData.Length - audioStart);
                    }
                }
            }
            else if (result.MessageType == WebSocketMessageType.Text)
            {
                string msg = Encoding.UTF8.GetString(msgData);
                if (msg.Contains("Path:turn.end"))
                {
                    done = true;
                }
            }
        }

        // Закрываем WebSocket
        if (ws.State == WebSocketState.Open)
        {
            try { await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None); }
            catch { }
        }

        if (audioStream.Length == 0)
            throw new Exception("Сервер не вернул аудиоданных");

        // Записываем файл
        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        await File.WriteAllBytesAsync(outputPath, audioStream.ToArray(), ct);
    }

    private static async Task SendTextAsync(ClientWebSocket ws, string message, CancellationToken ct)
    {
        byte[] data = Encoding.UTF8.GetBytes(message);
        await ws.SendAsync(new ArraySegment<byte>(data),
            WebSocketMessageType.Text, true, ct);
    }

    /// <summary>
    /// Получает список доступных голосов с сервера.
    /// </summary>
    public static async Task<List<VoiceInfo>> GetVoicesAsync(string languageFilter = "")
    {
        using var http = new HttpClient();
        http.DefaultRequestHeaders.Add("User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)");
        string json = await http.GetStringAsync(VOICE_LIST_URL);

        var voices = Newtonsoft.Json.JsonConvert.DeserializeObject<List<VoiceInfo>>(json) ?? [];

        if (!string.IsNullOrEmpty(languageFilter))
        {
            string filter = languageFilter.ToLower();
            voices = voices.Where(v =>
                v.Locale.ToLower().Contains(filter) ||
                v.ShortName.ToLower().Contains(filter)).ToList();
        }

        return voices.OrderBy(v => v.Locale).ToList();
    }
}

public class VoiceInfo
{
    public string Name { get; set; } = "";
    public string ShortName { get; set; } = "";
    public string Gender { get; set; } = "";
    public string Locale { get; set; } = "";
    public string FriendlyName { get; set; } = "";
}
