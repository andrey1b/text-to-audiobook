using System.IO;
using System.Speech.Synthesis;
using NAudio.Wave;
using NAudio.Lame;

namespace TextToAudiobookCSharp;

/// <summary>
/// Оффлайн-движок синтеза речи через Windows SAPI (System.Speech).
/// Не требует интернета. Использует голоса, установленные в системе.
/// </summary>
public class OfflineTtsEngine
{
    /// <summary>
    /// Синтезирует текст в MP3-файл через Windows SAPI.
    /// SAPI COM требует STA-поток — используем выделенный поток вместо Task.Run().
    /// </summary>
    public async Task SynthesizeAsync(
        string text, string voiceId, int speedPercent, string outputPath,
        Action<string>? log = null, CancellationToken ct = default)
    {
        // SAPI COM-объекты требуют STA (Single-Threaded Apartment).
        // Task.Run() использует потоки из пула (MTA) — это вызывает сбой SAPI.
        // Создаём выделенный STA-поток.
        Exception? synthException = null;
        var tcs = new TaskCompletionSource<bool>();

        var staThread = new Thread(() =>
        {
            try
            {
                ct.ThrowIfCancellationRequested();

                string wavPath = outputPath.Replace(".mp3", "_tmp_sapi.wav");

                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

                    using (var synth = new SpeechSynthesizer())
                    {
                        // Устанавливаем голос
                        try
                        {
                            synth.SelectVoice(voiceId);
                        }
                        catch
                        {
                            // Если не удалось выбрать голос по ID, пробуем по имени
                            try
                            {
                                var voices = synth.GetInstalledVoices();
                                var match = voices.FirstOrDefault(v =>
                                    v.VoiceInfo.Id == voiceId ||
                                    v.VoiceInfo.Name == voiceId ||
                                    v.VoiceInfo.Description.Contains(voiceId));
                                if (match != null)
                                    synth.SelectVoice(match.VoiceInfo.Name);
                            }
                            catch { /* используем голос по умолчанию */ }
                        }

                        // Скорость: SAPI rate от -10 до 10, наш speedPercent от -50 до 50
                        int sapiRate = Math.Clamp(speedPercent / 5, -10, 10);
                        synth.Rate = sapiRate;

                        // Сохраняем в WAV
                        synth.SetOutputToWaveFile(wavPath);
                        synth.Speak(text);
                        synth.SetOutputToNull();
                    }

                    ct.ThrowIfCancellationRequested();

                    if (!File.Exists(wavPath) || new FileInfo(wavPath).Length < 100)
                        throw new Exception("SAPI не создал аудиофайл.");

                    // Конвертируем WAV → MP3
                    ConvertWavToMp3(wavPath, outputPath);
                }
                finally
                {
                    // Удаляем временный WAV
                    try { if (File.Exists(wavPath)) File.Delete(wavPath); }
                    catch { }
                }

                tcs.TrySetResult(true);
            }
            catch (Exception ex)
            {
                synthException = ex;
                tcs.TrySetResult(false);
            }
        });

        staThread.SetApartmentState(ApartmentState.STA);
        staThread.IsBackground = true;
        staThread.Start();

        await tcs.Task;

        if (synthException != null)
            throw synthException;
    }

    /// <summary>
    /// Конвертирует WAV в MP3 через NAudio + LAME.
    /// </summary>
    private static void ConvertWavToMp3(string wavPath, string mp3Path)
    {
        try
        {
            using var reader = new WaveFileReader(wavPath);
            using var writer = new LameMP3FileWriter(mp3Path, reader.WaveFormat, LAMEPreset.MEDIUM);
            reader.CopyTo(writer);
        }
        catch
        {
            // Если LAME не сработал — копируем WAV как есть
            File.Copy(wavPath, mp3Path, overwrite: true);
        }
    }

    /// <summary>
    /// Получает список установленных SAPI-голосов.
    /// Выполняется в STA-потоке для корректной работы COM.
    /// </summary>
    public static List<OfflineVoiceInfo> GetInstalledVoices()
    {
        List<OfflineVoiceInfo>? result = null;

        // Если текущий поток уже STA — выполняем напрямую
        if (Thread.CurrentThread.GetApartmentState() == ApartmentState.STA)
        {
            result = GetInstalledVoicesInternal();
        }
        else
        {
            // Создаём STA-поток для доступа к SAPI COM
            var staThread = new Thread(() =>
            {
                result = GetInstalledVoicesInternal();
            });
            staThread.SetApartmentState(ApartmentState.STA);
            staThread.IsBackground = true;
            staThread.Start();
            staThread.Join();
        }

        return result ?? [];
    }

    private static List<OfflineVoiceInfo> GetInstalledVoicesInternal()
    {
        var result = new List<OfflineVoiceInfo>();
        try
        {
            using var synth = new SpeechSynthesizer();
            foreach (var voice in synth.GetInstalledVoices())
            {
                if (!voice.Enabled) continue;
                var info = voice.VoiceInfo;

                string culture = info.Culture?.TwoLetterISOLanguageName ?? "";

                // Оставляем только русские и английские голоса
                if (culture != "ru" && culture != "en") continue;
                string langTag = culture switch
                {
                    "ru" => "рус.",
                    "en" => "англ.",
                    _ => culture,
                };

                string gender = info.Gender switch
                {
                    VoiceGender.Male => "муж.",
                    VoiceGender.Female => "жен.",
                    _ => "",
                };

                string displayName = $"[Оффлайн] {info.Name}";
                if (!string.IsNullOrEmpty(langTag))
                    displayName += $" ({langTag}{(gender != "" ? $" {gender}" : "")})";

                result.Add(new OfflineVoiceInfo
                {
                    DisplayName = displayName,
                    VoiceId = info.Name,
                    Language = culture,
                    Gender = info.Gender.ToString(),
                });
            }
        }
        catch { }
        return result;
    }

    /// <summary>
    /// Подбирает оффлайн-голос по языку Edge-голоса.
    /// </summary>
    public static string FindOfflineVoiceFor(string edgeVoice, List<OfflineVoiceInfo> voices)
    {
        string lang = edgeVoice.Split('-')[0].ToLower();

        // Сначала ищем по языку
        var match = voices.FirstOrDefault(v => v.Language == lang);
        if (match != null) return match.VoiceId;

        // Иначе — первый доступный
        return voices.Count > 0 ? voices[0].VoiceId : "";
    }
}

public class OfflineVoiceInfo
{
    public string DisplayName { get; set; } = "";
    public string VoiceId { get; set; } = "";
    public string Language { get; set; } = "";
    public string Gender { get; set; } = "";
}
