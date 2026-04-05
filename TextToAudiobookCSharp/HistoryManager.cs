using System.IO;
using Newtonsoft.Json;

namespace TextToAudiobookCSharp;

/// <summary>
/// Управление историей проектов (последние книги).
/// Аналог Python-модуля audiobook_history.json.
/// </summary>
public static class HistoryManager
{
    private const int MaxHistory = 10;

    private static string HistoryPath()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        return Path.Combine(baseDir, "audiobook_history.json");
    }

    public static List<HistoryEntry> LoadHistory()
    {
        string path = HistoryPath();
        if (!File.Exists(path)) return [];

        try
        {
            string json = File.ReadAllText(path, System.Text.Encoding.UTF8);
            return JsonConvert.DeserializeObject<List<HistoryEntry>>(json) ?? [];
        }
        catch
        {
            return [];
        }
    }

    public static void SaveHistory(List<HistoryEntry> history)
    {
        try
        {
            string json = JsonConvert.SerializeObject(history, Formatting.Indented);
            File.WriteAllText(HistoryPath(), json, System.Text.Encoding.UTF8);
        }
        catch { }
    }

    public static void AddToHistory(
        string inputFile, string outputDir, string voice,
        int totalChapters, int doneChapters)
    {
        var history = LoadHistory();
        string normInput = Path.GetFullPath(inputFile);
        string now = DateTime.Now.ToString("yyyy-MM-dd HH:mm");

        var existing = history.FirstOrDefault(e =>
            Path.GetFullPath(e.InputFile ?? "") == normInput);

        if (existing != null)
        {
            existing.OutputDir = outputDir;
            existing.Voice = voice;
            existing.TotalChapters = totalChapters;
            existing.DoneChapters = doneChapters;
            existing.Finished = doneChapters >= totalChapters;
            existing.LastUsed = now;
            history.Remove(existing);
            history.Insert(0, existing);
        }
        else
        {
            history.Insert(0, new HistoryEntry
            {
                InputFile = inputFile,
                OutputDir = outputDir,
                Voice = voice,
                TotalChapters = totalChapters,
                DoneChapters = doneChapters,
                Finished = doneChapters >= totalChapters,
                LastUsed = now,
                BookName = Path.GetFileNameWithoutExtension(inputFile),
            });
        }

        if (history.Count > MaxHistory)
            history = history.Take(MaxHistory).ToList();

        SaveHistory(history);
    }

    public static HistoryEntry? GetLastUnfinished()
    {
        return LoadHistory().FirstOrDefault(e =>
            !e.Finished && File.Exists(e.InputFile ?? ""));
    }
}

public class HistoryEntry
{
    [JsonProperty("input_file")] public string? InputFile { get; set; }
    [JsonProperty("output_dir")] public string? OutputDir { get; set; }
    [JsonProperty("voice")] public string? Voice { get; set; }
    [JsonProperty("total_chapters")] public int TotalChapters { get; set; }
    [JsonProperty("done_chapters")] public int DoneChapters { get; set; }
    [JsonProperty("finished")] public bool Finished { get; set; }
    [JsonProperty("last_used")] public string? LastUsed { get; set; }
    [JsonProperty("book_name")] public string? BookName { get; set; }
}
