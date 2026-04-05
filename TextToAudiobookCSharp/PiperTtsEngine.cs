using System.Diagnostics;
using System.IO;
using NAudio.Wave;
using NAudio.Lame;

namespace TextToAudiobookCSharp;

/// <summary>
/// Информация о голосовой модели Piper.
/// </summary>
public class PiperVoiceInfo
{
    public string DisplayName { get; set; } = "";
    public string ModelPath { get; set; } = "";
    public string Language { get; set; } = "";
}

/// <summary>
/// TTS-движок на основе Piper — быстрый локальный нейросетевой синтез речи.
/// Качество значительно выше Windows SAPI, работает полностью оффлайн.
///
/// Ожидаемая структура:
///   piper/
///     piper.exe
///     *.onnx          — модели голосов
///     *.onnx.json     — конфигурация моделей
/// </summary>
public class PiperTtsEngine
{
    /// <summary>
    /// Синтезирует текст в MP3-файл через Piper TTS.
    /// </summary>
    public async Task SynthesizeAsync(
        string text, string modelPath, double lengthScale, string outputPath,
        Action<string>? log = null, CancellationToken ct = default)
    {
        string piperExe = FindPiperExe();
        if (string.IsNullOrEmpty(piperExe))
            throw new FileNotFoundException(
                "piper.exe не найден. Поместите Piper TTS в папку 'piper' рядом с программой.");

        if (!File.Exists(modelPath))
            throw new FileNotFoundException($"Модель Piper не найдена: {modelPath}");

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

        string wavPath = Path.ChangeExtension(outputPath, ".piper_tmp.wav");

        try
        {
            ct.ThrowIfCancellationRequested();

            // Запускаем piper.exe: текст через stdin → WAV на выходе
            var psi = new ProcessStartInfo
            {
                FileName = piperExe,
                Arguments = $"--model \"{modelPath}\" --output_file \"{wavPath}\" --length_scale {lengthScale:F2} --sentence_silence 0.3",
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardInputEncoding = System.Text.Encoding.UTF8,
            };

            using var process = new Process { StartInfo = psi };
            process.Start();

            // Передаём текст через stdin
            await process.StandardInput.WriteAsync(text);
            process.StandardInput.Close();

            // Ждём завершения (с таймаутом и отменой)
            string stderr = "";
            var stderrTask = process.StandardError.ReadToEndAsync();

            using var reg = ct.Register(() =>
            {
                try { process.Kill(); } catch { }
            });

            await process.WaitForExitAsync(ct);
            stderr = await stderrTask;

            if (process.ExitCode != 0)
                throw new Exception($"Piper завершился с ошибкой (код {process.ExitCode}): {stderr.Trim()}");

            ct.ThrowIfCancellationRequested();

            if (!File.Exists(wavPath) || new FileInfo(wavPath).Length < 100)
                throw new Exception("Piper не создал аудиофайл.");

            // Конвертируем WAV → MP3
            ConvertWavToMp3(wavPath, outputPath);
        }
        finally
        {
            try { if (File.Exists(wavPath)) File.Delete(wavPath); } catch { }
        }
    }

    /// <summary>
    /// Ищет piper.exe в папке 'piper' рядом с исполняемым файлом.
    /// </summary>
    public static string? FindPiperExe()
    {
        string? exeDir = Path.GetDirectoryName(Environment.ProcessPath);
        if (exeDir == null) return null;

        // 1. piper/piper.exe рядом с exe
        string path1 = Path.Combine(exeDir, "piper", "piper.exe");
        if (File.Exists(path1)) return path1;

        // 2. piper.exe прямо рядом с exe
        string path2 = Path.Combine(exeDir, "piper.exe");
        if (File.Exists(path2)) return path2;

        // 3. Рабочая директория
        string path3 = Path.Combine(Directory.GetCurrentDirectory(), "piper", "piper.exe");
        if (File.Exists(path3)) return path3;

        return null;
    }

    /// <summary>
    /// Ищет модели (.onnx) в папке piper рядом с exe.
    /// Возвращает список найденных голосов (только ru/en).
    /// </summary>
    public static List<PiperVoiceInfo> GetAvailableVoices()
    {
        var result = new List<PiperVoiceInfo>();

        string? piperDir = GetPiperDir();
        if (piperDir == null || !Directory.Exists(piperDir)) return result;

        foreach (string onnxFile in Directory.GetFiles(piperDir, "*.onnx"))
        {
            string fileName = Path.GetFileNameWithoutExtension(onnxFile);
            string jsonConfig = onnxFile + ".json";

            // Проверяем наличие конфигурации
            if (!File.Exists(jsonConfig)) continue;

            // Определяем язык из имени файла (ru_RU-dmitri-medium → ru)
            string lang = "";
            string voiceName = fileName;

            if (fileName.StartsWith("ru_RU", StringComparison.OrdinalIgnoreCase) ||
                fileName.StartsWith("ru-RU", StringComparison.OrdinalIgnoreCase))
            {
                lang = "ru";
            }
            else if (fileName.StartsWith("en_US", StringComparison.OrdinalIgnoreCase) ||
                     fileName.StartsWith("en_GB", StringComparison.OrdinalIgnoreCase) ||
                     fileName.StartsWith("en-US", StringComparison.OrdinalIgnoreCase) ||
                     fileName.StartsWith("en-GB", StringComparison.OrdinalIgnoreCase))
            {
                lang = "en";
            }
            else
            {
                // Пропускаем модели других языков
                continue;
            }

            // Извлекаем имя голоса: ru_RU-dmitri-medium → dmitri
            string shortName = fileName;
            var parts = fileName.Split('-', '_');
            if (parts.Length >= 3)
                shortName = parts[2]; // locale_REGION-name-quality → name

            string langTag = lang == "ru" ? "рус." : "англ.";
            string displayName = $"[Piper] {shortName} ({langTag})";

            result.Add(new PiperVoiceInfo
            {
                DisplayName = displayName,
                ModelPath = onnxFile,
                Language = lang,
            });
        }

        return result;
    }

    /// <summary>
    /// Подбирает Piper-голос по языку Edge-голоса.
    /// </summary>
    public static string FindPiperModelFor(string edgeVoice, List<PiperVoiceInfo> voices)
    {
        string lang = edgeVoice.Split('-')[0].ToLower();

        var match = voices.FirstOrDefault(v => v.Language == lang);
        if (match != null) return match.ModelPath;

        return voices.Count > 0 ? voices[0].ModelPath : "";
    }

    /// <summary>
    /// Проверяет, доступен ли Piper TTS (exe + хотя бы одна модель).
    /// </summary>
    public static bool IsAvailable()
    {
        return FindPiperExe() != null && GetAvailableVoices().Count > 0;
    }

    private static string? GetPiperDir()
    {
        string? exeDir = Path.GetDirectoryName(Environment.ProcessPath);
        if (exeDir == null) return null;

        string dir1 = Path.Combine(exeDir, "piper");
        if (Directory.Exists(dir1)) return dir1;

        string dir2 = Path.Combine(Directory.GetCurrentDirectory(), "piper");
        if (Directory.Exists(dir2)) return dir2;

        return null;
    }

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
}
