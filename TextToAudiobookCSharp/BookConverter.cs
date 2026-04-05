using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using NAudio.Wave;
using NAudio.Lame;
using UtfUnknown;

namespace TextToAudiobookCSharp;

/// <summary>
/// Режим TTS-синтеза.
/// </summary>
public enum TtsMode
{
    Auto,
    Online,
    Offline,
    Piper,
}

/// <summary>
/// Основной конвертер книги: чтение текста, разбивка на главы,
/// генерация аудио, объединение.
/// </summary>
public class BookConverter
{
    // ── Голоса по умолчанию ──────────────────────────────────────────
    public static readonly Dictionary<string, string> DefaultVoices = new()
    {
        ["ru"] = "ru-RU-DmitryNeural",
        ["en"] = "en-US-GuyNeural",
    };

    public static readonly List<(string DisplayName, string ShortName)> VoicePresets =
    [
        ("Дмитрий (рус. муж.)", "ru-RU-DmitryNeural"),
        ("Светлана (рус. жен.)", "ru-RU-SvetlanaNeural"),
        ("Guy (англ. муж.)", "en-US-GuyNeural"),
        ("Jenny (англ. жен.)", "en-US-JennyNeural"),
    ];

    // ── Паттерны глав ────────────────────────────────────────────────
    private static readonly string[] ChapterPatterns =
    [
        @"^Глава\s+\d+", @"^ГЛАВА\s+\d+",
        @"^Chapter\s+\d+", @"^CHAPTER\s+\d+",
        @"^Часть\s+\d+", @"^ЧАСТЬ\s+\d+",
        @"^Part\s+\d+", @"^PART\s+\d+",
        @"^\d+\.\s+[A-ZА-ЯЁ]",
    ];

    private const int MaxChunkLen = 3000;
    private const int MinFileSize = 1024;

    private readonly EdgeTtsEngine _tts = new();
    private readonly OfflineTtsEngine _offlineTts = new();
    private readonly PiperTtsEngine _piperTts = new();

    /// <summary>
    /// Синтезирует текст, выбирая движок (онлайн/оффлайн).
    /// При провале онлайна автоматически переключается на оффлайн.
    /// </summary>
    private async Task SynthesizeChunkWithMode(
        string text, string voice, string speed, int speedPct,
        string outputPath, TtsMode mode, List<OfflineVoiceInfo> offlineVoices,
        List<PiperVoiceInfo>? piperVoices,
        Action<string>? log, CancellationToken ct)
    {
        if (mode == TtsMode.Piper && piperVoices != null && piperVoices.Count > 0)
        {
            // voice содержит путь к .onnx модели (для Piper)
            string modelPath = voice;

            // Если voice — не путь к файлу, подбираем модель по языку
            if (!File.Exists(modelPath))
                modelPath = PiperTtsEngine.FindPiperModelFor(voice, piperVoices);

            // length_scale: speedPct от -50..+50 → 1.5..0.5
            double lengthScale = 1.0 - (speedPct / 100.0);
            lengthScale = Math.Clamp(lengthScale, 0.3, 2.0);

            await _piperTts.SynthesizeAsync(text, modelPath, lengthScale, outputPath, log, ct);
            return;
        }

        if (mode == TtsMode.Offline)
        {
            await _offlineTts.SynthesizeAsync(text, voice, speedPct, outputPath, log, ct);
            return;
        }

        // Онлайн — с автопереключением на оффлайн/piper при неудаче
        try
        {
            await _tts.SynthesizeAsync(text, voice, speed, outputPath, log, ct);
        }
        catch (Exception ex) when (piperVoices != null && piperVoices.Count > 0)
        {
            log?.Invoke($"  Онлайн-синтез не удался: {ex.Message}");
            log?.Invoke("  Переключаюсь на Piper TTS...");
            string modelPath = PiperTtsEngine.FindPiperModelFor(voice, piperVoices);
            double lengthScale = 1.0 - (speedPct / 100.0);
            lengthScale = Math.Clamp(lengthScale, 0.3, 2.0);
            await _piperTts.SynthesizeAsync(text, modelPath, lengthScale, outputPath, log, ct);
        }
        catch (Exception ex) when (offlineVoices.Count > 0)
        {
            log?.Invoke($"  Онлайн-синтез не удался: {ex.Message}");
            log?.Invoke("  Переключаюсь на оффлайн (SAPI)...");
            string offlineVoice = OfflineTtsEngine.FindOfflineVoiceFor(voice, offlineVoices);
            await _offlineTts.SynthesizeAsync(text, offlineVoice, speedPct, outputPath, log, ct);
        }
    }

    // ── Определение кодировки ────────────────────────────────────────

    public static string DetectEncoding(string filePath, Action<string>? log = null)
    {
        byte[] raw = File.ReadAllBytes(filePath);

        // BOM
        if (raw.Length >= 3 && raw[0] == 0xEF && raw[1] == 0xBB && raw[2] == 0xBF)
        {
            log?.Invoke("Кодировка: UTF-8 (BOM)");
            return "utf-8";
        }
        if (raw.Length >= 2 && ((raw[0] == 0xFF && raw[1] == 0xFE) || (raw[0] == 0xFE && raw[1] == 0xFF)))
        {
            log?.Invoke("Кодировка: UTF-16 (BOM)");
            return "utf-16";
        }

        // Автоопределение через UTF.Unknown (аналог chardet)
        try
        {
            var result = CharsetDetector.DetectFromBytes(raw.Take(102400).ToArray());
            if (result.Detected != null)
            {
                string enc = result.Detected.EncodingName;
                double conf = result.Detected.Confidence;
                log?.Invoke($"Кодировка: {enc} (уверенность: {conf:P0})");

                // Проверяем что реально работает
                try
                {
                    Encoding.GetEncoding(enc).GetString(raw);
                    return enc;
                }
                catch { log?.Invoke($"  Предположение {enc} не подошло, пробую utf-8..."); }
            }
        }
        catch { }

        // Fallback
        string[] tryEncodings = ["utf-8", "windows-1251", "cp866", "koi8-r", "iso-8859-5", "latin1"];
        foreach (var enc in tryEncodings)
        {
            try
            {
                Encoding.GetEncoding(enc).GetString(raw);
                log?.Invoke($"Кодировка (подбор): {enc}");
                return enc;
            }
            catch { }
        }

        log?.Invoke("Кодировка: не удалось определить, использую utf-8");
        return "utf-8";
    }

    // ── Определение языка ────────────────────────────────────────────

    public static string DetectLanguage(string text)
    {
        string sample = text.Length > 5000 ? text[..5000] : text;
        int cyrillic = sample.Count(c => c >= '\u0400' && c <= '\u04FF');
        int latin = sample.Count(c => (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
        return cyrillic > latin ? "ru" : "en";
    }

    // ── Разбивка на главы ────────────────────────────────────────────

    public static List<(string Title, string Body)> SplitIntoChapters(string text)
    {
        string combinedPattern = string.Join("|", ChapterPatterns.Select(p => $"({p})"));
        string[] lines = text.Split('\n');

        var chapters = new List<(string Title, string Body)>();
        string currentTitle = "";
        var currentLines = new List<string>();

        foreach (string line in lines)
        {
            if (Regex.IsMatch(line.Trim(), combinedPattern, RegexOptions.IgnoreCase))
            {
                if (currentLines.Count > 0)
                {
                    string body = string.Join("\n", currentLines).Trim();
                    if (!string.IsNullOrEmpty(body))
                        chapters.Add((currentTitle, body));
                }
                currentTitle = line.Trim();
                currentLines.Clear();
            }
            else
            {
                currentLines.Add(line);
            }
        }

        if (currentLines.Count > 0)
        {
            string body = string.Join("\n", currentLines).Trim();
            if (!string.IsNullOrEmpty(body))
                chapters.Add((currentTitle, body));
        }

        return chapters.Count <= 1 ? [("", text.Trim())] : chapters;
    }

    // ── Разбивка текста на части для TTS ─────────────────────────────

    public static List<string> SplitTextIntoChunks(string text, int maxLen = MaxChunkLen)
    {
        var paragraphs = Regex.Split(text, @"\n\s*\n");
        var chunks = new List<string>();
        string current = "";

        foreach (string rawPara in paragraphs)
        {
            string para = rawPara.Trim();
            if (string.IsNullOrEmpty(para)) continue;

            if (para.Length > maxLen)
            {
                var sentences = Regex.Split(para, @"(?<=[.!?])\s+");
                foreach (string sentence in sentences)
                {
                    if (current.Length + sentence.Length + 1 > maxLen)
                    {
                        if (!string.IsNullOrEmpty(current))
                            chunks.Add(current.Trim());
                        current = sentence;
                    }
                    else
                    {
                        current = string.IsNullOrEmpty(current) ? sentence : current + " " + sentence;
                    }
                }
                continue;
            }

            if (current.Length + para.Length + 2 > maxLen)
            {
                if (!string.IsNullOrEmpty(current))
                    chunks.Add(current.Trim());
                current = para;
            }
            else
            {
                current = string.IsNullOrEmpty(current) ? para : current + "\n\n" + para;
            }
        }

        if (!string.IsNullOrWhiteSpace(current))
            chunks.Add(current.Trim());

        return chunks;
    }

    // ── Объединение MP3-файлов ───────────────────────────────────────

    public static async Task MergeFilesAsync(
        List<string> files, string outputPath, Action<string>? log = null)
    {
        log?.Invoke("Объединение фрагментов в один файл...");

        // Простое склеивание MP3 байтов (все файлы одного формата от Edge TTS)
        using var outStream = File.Create(outputPath);
        foreach (string file in files)
        {
            if (File.Exists(file))
            {
                byte[] data = await File.ReadAllBytesAsync(file);
                await outStream.WriteAsync(data);
            }
        }
        log?.Invoke($"Объединённый файл: {outputPath}");
    }

    // ── Форматирование времени ───────────────────────────────────────

    // ── Проверка интернета ───────────────────────────────────────────

    public static bool CheckInternet(double timeoutSeconds = 3.0)
    {
        try
        {
            using var client = new TcpClient();
            var task = client.ConnectAsync("speech.platform.bing.com", 443);
            return task.Wait(TimeSpan.FromSeconds(timeoutSeconds));
        }
        catch { return false; }
    }

    /// <summary>
    /// Определяет фактический TTS-режим (online/offline) из auto.
    /// </summary>
    public static TtsMode ResolveTtsMode(TtsMode mode, Action<string>? log = null)
    {
        if (mode == TtsMode.Online) return TtsMode.Online;
        if (mode == TtsMode.Offline) return TtsMode.Offline;
        if (mode == TtsMode.Piper) return TtsMode.Piper;

        // Auto: онлайн → piper → sapi
        log?.Invoke("Проверка интернет-подключения...");
        if (CheckInternet())
        {
            log?.Invoke("Интернет доступен → режим: Онлайн (Edge TTS)");
            return TtsMode.Online;
        }
        else
        {
            // Нет интернета — пробуем Piper
            if (PiperTtsEngine.IsAvailable())
            {
                var piperVoices = PiperTtsEngine.GetAvailableVoices();
                log?.Invoke($"Интернет недоступен → режим: Piper TTS (моделей: {piperVoices.Count})");
                return TtsMode.Piper;
            }

            // Нет Piper — пробуем SAPI
            var offlineVoices = OfflineTtsEngine.GetInstalledVoices();
            if (offlineVoices.Count > 0)
            {
                log?.Invoke($"Интернет недоступен → режим: Оффлайн (Windows SAPI, голосов: {offlineVoices.Count})");
                return TtsMode.Offline;
            }
            log?.Invoke("Интернет недоступен, оффлайн-движки не найдены. Попробую онлайн...");
            return TtsMode.Online;
        }
    }

    // ── Форматирование времени ───────────────────────────────────────

    public static string FormatTime(double seconds)
    {
        int s = (int)seconds;
        if (s < 60) return $"{s} сек";
        if (s < 3600) return $"{s / 60} мин {s % 60} сек";
        return $"{s / 3600} ч {s % 3600 / 60} мин";
    }

    // ── Основная функция конвертации ─────────────────────────────────

    public async Task<ConversionResult?> ConvertBookAsync(ConversionOptions opts)
    {
        var log = opts.Log ?? (_ => { });
        var sw = System.Diagnostics.Stopwatch.StartNew();

        if (!File.Exists(opts.InputFile))
        {
            log($"Ошибка: файл '{opts.InputFile}' не найден.");
            return null;
        }

        // Определяем фактический режим TTS
        var actualMode = ResolveTtsMode(opts.TtsMode, log);
        var offlineVoices = OfflineTtsEngine.GetInstalledVoices();
        var piperVoices = PiperTtsEngine.GetAvailableVoices();

        log($"Чтение файла: {opts.InputFile}");

        // Определение кодировки
        string encoding = opts.Encoding;
        if (encoding == "auto")
            encoding = DetectEncoding(opts.InputFile, log);

        string text;
        try
        {
            text = File.ReadAllText(opts.InputFile, Encoding.GetEncoding(encoding));
        }
        catch
        {
            text = File.ReadAllText(opts.InputFile, Encoding.UTF8);
        }

        if (string.IsNullOrWhiteSpace(text))
        {
            log("Ошибка: файл пуст.");
            return null;
        }

        string lang = DetectLanguage(text);
        string voice;
        if (!string.IsNullOrEmpty(opts.Voice))
        {
            voice = opts.Voice;
        }
        else if (actualMode == TtsMode.Piper && piperVoices.Count > 0)
        {
            string edgeDefault = DefaultVoices.GetValueOrDefault(lang, "en-US-GuyNeural");
            voice = PiperTtsEngine.FindPiperModelFor(edgeDefault, piperVoices);
        }
        else if (actualMode == TtsMode.Offline && offlineVoices.Count > 0)
        {
            string edgeDefault = DefaultVoices.GetValueOrDefault(lang, "en-US-GuyNeural");
            voice = OfflineTtsEngine.FindOfflineVoiceFor(edgeDefault, offlineVoices);
        }
        else
        {
            voice = DefaultVoices.GetValueOrDefault(lang, "en-US-GuyNeural");
        }
        string modeLabel = actualMode switch
        {
            TtsMode.Online => "Онлайн (Edge TTS)",
            TtsMode.Piper => "Piper TTS (нейросеть, оффлайн)",
            TtsMode.Offline => "Оффлайн (Windows SAPI)",
            _ => "Авто",
        };
        log($"Режим: {modeLabel}");
        log($"Язык: {lang}, голос: {voice}");

        var chapters = opts.NoChapters
            ? [("", text.Trim())]
            : SplitIntoChapters(text);
        log($"Найдено глав/частей: {chapters.Count}");

        string outDir = opts.OutputDir;
        Directory.CreateDirectory(outDir);

        // ── Умная проверка готовых фрагментов ───────────────────────
        log("\nПроверка готовых фрагментов...");

        var chapterPaths = new List<string>();
        for (int i = 0; i < chapters.Count; i++)
        {
            string safeTitle = !string.IsNullOrEmpty(chapters[i].Title)
                ? Regex.Replace(chapters[i].Title, @"[<>:""/\\|?*]", "_")
                : "";
            if (safeTitle.Length > 50) safeTitle = safeTitle[..50];

            string filename = $"{i + 1:D3}";
            if (!string.IsNullOrEmpty(safeTitle))
                filename += $"_{safeTitle}";
            filename += ".mp3";
            chapterPaths.Add(Path.Combine(outDir, filename));
        }

        // Находим первый отсутствующий
        int firstMissing = chapters.Count;
        for (int i = 0; i < chapters.Count; i++)
        {
            if (!File.Exists(chapterPaths[i]) || new FileInfo(chapterPaths[i]).Length < MinFileSize)
            {
                firstMissing = i;
                break;
            }
        }

        var filesToGenerate = new List<(int Index, string Title, string Body, string Path)>();
        var generatedFiles = new List<string>();

        for (int i = 0; i < chapters.Count; i++)
        {
            generatedFiles.Add(chapterPaths[i]);
            if (i < firstMissing) continue;
            if (File.Exists(chapterPaths[i]) && new FileInfo(chapterPaths[i]).Length >= MinFileSize)
                continue;
            filesToGenerate.Add((i + 1, chapters[i].Title, chapters[i].Body, chapterPaths[i]));
        }

        int skipped = chapters.Count - filesToGenerate.Count;
        if (skipped > 0)
            log($"Готовых фрагментов: {skipped} из {chapters.Count} — пропускаю");

        bool stopped = false;

        if (filesToGenerate.Count == 0)
        {
            log("\nВсе фрагменты уже сгенерированы!");
            opts.Progress?.Invoke(chapters.Count, chapters.Count);
            opts.TimeEstimate?.Invoke("");
        }
        else
        {
            int remaining = filesToGenerate.Count;
            log($"Осталось сгенерировать: {remaining}\n");
            log("Генерация аудио...\n");

            var chunkTimes = new List<double>();

            for (int idx = 0; idx < filesToGenerate.Count; idx++)
            {
                var (chNum, title, body, filePath) = filesToGenerate[idx];

                // Проверка остановки
                if (opts.CancelToken.IsCancellationRequested)
                {
                    log("\nОстановлено пользователем. Прогресс сохранён.");
                    opts.TimeEstimate?.Invoke("");
                    stopped = true;
                    break;
                }

                // Проверка паузы
                if (opts.PauseToken != null && opts.PauseToken.IsPaused)
                {
                    log("\nПауза. Можно сменить голос в настройках.");
                    log("Нажмите «Продолжить» для возобновления.\n");
                    opts.TimeEstimate?.Invoke("Пауза");

                    while (opts.PauseToken.IsPaused)
                    {
                        if (opts.CancelToken.IsCancellationRequested) break;
                        await Task.Delay(500);
                    }

                    if (opts.CancelToken.IsCancellationRequested)
                    {
                        log("\nОстановлено пользователем. Прогресс сохранён.");
                        opts.TimeEstimate?.Invoke("");
                        stopped = true;
                        break;
                    }

                    // Проверяем смену голоса
                    if (opts.VoiceFunc != null)
                    {
                        string newVoice = opts.VoiceFunc();
                        if (!string.IsNullOrEmpty(newVoice) && newVoice != voice)
                        {
                            log($"Голос изменён: {voice} → {newVoice}");
                            voice = newVoice;
                        }
                    }
                    log("Продолжение...\n");
                }

                var chunkSw = System.Diagnostics.Stopwatch.StartNew();

                // Синтезируем главу
                string label = !string.IsNullOrEmpty(title) ? title : $"Часть {chNum}";
                log($"[{chNum}/{chapters.Count}] {label}");

                var chunks = SplitTextIntoChunks(body);

                // Вычисляем speedPercent для оффлайн-движка
                int speedPct = 0;
                try { speedPct = int.Parse(opts.Speed.Replace("%", "").Replace("+", "")); }
                catch { }

                if (chunks.Count == 1)
                {
                    await SynthesizeChunkWithMode(chunks[0], voice, opts.Speed,
                        speedPct, filePath, actualMode, offlineVoices, piperVoices, log, opts.CancelToken);
                }
                else
                {
                    var tempFiles = new List<string>();
                    for (int ci = 0; ci < chunks.Count; ci++)
                    {
                        string tempPath = filePath.Replace(".mp3", $"_part{ci:D4}.mp3");
                        tempFiles.Add(tempPath);
                        log($"  фрагмент {ci + 1}/{chunks.Count}...");
                        await SynthesizeChunkWithMode(chunks[ci], voice, opts.Speed,
                            speedPct, tempPath, actualMode, offlineVoices, piperVoices, log, opts.CancelToken);
                    }

                    // Склеиваем части главы
                    using (var outStream = File.Create(filePath))
                    {
                        foreach (string tf in tempFiles)
                        {
                            if (File.Exists(tf))
                            {
                                byte[] data = await File.ReadAllBytesAsync(tf);
                                await outStream.WriteAsync(data);
                            }
                        }
                    }

                    // Удаляем временные
                    foreach (string tf in tempFiles)
                        try { File.Delete(tf); } catch { }
                }

                chunkSw.Stop();
                double chunkElapsed = chunkSw.Elapsed.TotalSeconds;
                chunkTimes.Add(chunkElapsed);

                int done = skipped + idx + 1;
                opts.Progress?.Invoke(done, chapters.Count);

                double avgTime = chunkTimes.Average();
                int left = remaining - (idx + 1);
                if (left > 0)
                {
                    double eta = avgTime * left;
                    opts.TimeEstimate?.Invoke($"Осталось ~{FormatTime(eta)}");
                }
                else
                {
                    opts.TimeEstimate?.Invoke("");
                }

                log($"  ({FormatTime(chunkElapsed)} на фрагмент," +
                    $" осталось ~{(left > 0 ? FormatTime(avgTime * left) : "0 сек")})\n");

                // Сохраняем прогресс
                HistoryManager.AddToHistory(opts.InputFile, outDir, voice, chapters.Count, done);
            }

            if (!stopped)
            {
                sw.Stop();
                log($"\nГенерация заняла: {FormatTime(sw.Elapsed.TotalSeconds)}");
            }
        }

        if (stopped) return null;

        // Финальная запись в историю
        HistoryManager.AddToHistory(opts.InputFile, outDir, voice, chapters.Count, chapters.Count);

        log($"\nГотово! Файлы сохранены в: {Path.GetFullPath(outDir)}");
        log("Папка с фрагментами сохранена для дальнейшего использования.");

        string? mergedPath = null;
        if (opts.Merge && generatedFiles.Count > 1)
        {
            string bookName = Path.GetFileNameWithoutExtension(opts.InputFile);
            mergedPath = Path.Combine(outDir, $"{bookName}_full.mp3");
            if (File.Exists(mergedPath)) File.Delete(mergedPath);
            await MergeFilesAsync(generatedFiles, mergedPath, log);

            // Удаление фрагментов после объединения (если пользователь выбрал)
            if (opts.DeleteFragments)
            {
                log("Удаление фрагментов...");
                int deleted = 0;
                foreach (string fragFile in generatedFiles)
                {
                    if (File.Exists(fragFile) && fragFile != mergedPath)
                    {
                        try { File.Delete(fragFile); deleted++; } catch { }
                    }
                }
                log($"Удалено фрагментов: {deleted}");
            }
        }

        long totalSize = generatedFiles.Where(File.Exists).Sum(f => new FileInfo(f).Length);
        log($"\nВсего файлов: {generatedFiles.Count}");
        log($"Общий размер: {totalSize / (1024.0 * 1024.0):F1} МБ");

        return new ConversionResult
        {
            OutputDir = Path.GetFullPath(outDir),
            MergedFile = mergedPath,
            TotalFiles = generatedFiles.Count,
            TotalSizeMb = Math.Round(totalSize / (1024.0 * 1024.0), 1),
            BookName = Path.GetFileNameWithoutExtension(opts.InputFile),
        };
    }
}

// ── Параметры конвертации ────────────────────────────────────────────

public class ConversionOptions
{
    public required string InputFile { get; set; }
    public required string OutputDir { get; set; }
    public string? Voice { get; set; }
    public string Speed { get; set; } = "+0%";
    public bool Merge { get; set; } = true;
    public bool DeleteFragments { get; set; }
    public bool NoChapters { get; set; }
    public string Encoding { get; set; } = "auto";
    public Action<string>? Log { get; set; }
    public Action<int, int>? Progress { get; set; }
    public Action<string>? TimeEstimate { get; set; }
    public CancellationToken CancelToken { get; set; }
    public PauseToken? PauseToken { get; set; }
    public Func<string>? VoiceFunc { get; set; }
    public TtsMode TtsMode { get; set; } = TtsMode.Auto;
}

// ── Результат конвертации ────────────────────────────────────────────

public class ConversionResult
{
    public string OutputDir { get; set; } = "";
    public string? MergedFile { get; set; }
    public int TotalFiles { get; set; }
    public double TotalSizeMb { get; set; }
    public string BookName { get; set; } = "";
}

// ── Токен паузы ──────────────────────────────────────────────────────

public class PauseToken
{
    private volatile bool _isPaused;
    public bool IsPaused => _isPaused;
    public void Pause() => _isPaused = true;
    public void Resume() => _isPaused = false;
}
