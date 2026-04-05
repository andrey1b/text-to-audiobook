using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using System.Linq;

namespace TextToAudiobookCSharp;

public partial class MainWindow : Window
{
    private readonly string[] _encodings =
        ["auto", "utf-8", "utf-8-sig", "utf-16", "windows-1251", "cp866", "koi8-r", "iso-8859-5", "latin1"];

    private bool _isConverting;
    private CancellationTokenSource? _cts;
    private PauseToken? _pauseToken;
    private HistoryEntry? _unfinished;
    private List<HistoryEntry> _history = [];
    private TtsMode _selectedTtsMode = TtsMode.Auto;

    // Объединённый список голосов (онлайн + оффлайн + piper)
    private List<(string DisplayName, string ShortName)> _allVoices = [];
    private List<OfflineVoiceInfo> _offlineVoices = [];
    private List<PiperVoiceInfo> _piperVoices = [];

    // Режимы
    private static readonly (string Label, TtsMode Mode)[] TtsModes =
    [
        ("Авто (онлайн → Piper → SAPI)", TtsMode.Auto),
        ("Онлайн (Edge TTS)", TtsMode.Online),
        ("Piper TTS (нейросеть, оффлайн)", TtsMode.Piper),
        ("Оффлайн (Windows SAPI)", TtsMode.Offline),
    ];

    public MainWindow()
    {
        InitializeComponent();
        InitControls();
        LoadHistoryUI();
    }

    // ── Инициализация контролов ──────────────────────────────────────

    private void InitControls()
    {
        // Оффлайн-голоса
        _offlineVoices = OfflineTtsEngine.GetInstalledVoices();
        _piperVoices = PiperTtsEngine.GetAvailableVoices();

        // Режим TTS
        ComboTtsMode.ItemsSource = TtsModes.Select(m => m.Label).ToList();
        ComboTtsMode.SelectedIndex = 0;

        // Голоса — онлайн + оффлайн
        UpdateVoiceList(TtsMode.Auto);

        // Кодировки
        ComboEncoding.ItemsSource = _encodings;
        ComboEncoding.SelectedIndex = 0;

        // Шрифт лога — моноширинные шрифты
        var monoFonts = new[] { "Consolas", "Courier New", "Lucida Console", "Cascadia Mono", "Source Code Pro" };
        var availableFonts = Fonts.SystemFontFamilies.Select(f => f.Source).OrderBy(f => f).ToList();
        var logFonts = monoFonts.Where(f => availableFonts.Contains(f)).ToList();
        if (logFonts.Count == 0) logFonts.Add("Consolas");
        ComboLogFont.ItemsSource = logFonts;
        ComboLogFont.SelectedIndex = 0;

        // Размер шрифта лога
        var fontSizes = Enumerable.Range(11, 14).Select(s => s.ToString()).ToList(); // 11..24
        ComboLogFontSize.ItemsSource = fontSizes;
        ComboLogFontSize.SelectedIndex = fontSizes.IndexOf("14"); // default 14
        if (ComboLogFontSize.SelectedIndex < 0) ComboLogFontSize.SelectedIndex = 0;
    }

    private void UpdateVoiceList(TtsMode mode)
    {
        var online = BookConverter.VoicePresets
            .Select(v => (v.DisplayName, v.ShortName)).ToList();
        var offline = _offlineVoices
            .Select(v => (v.DisplayName, v.VoiceId)).ToList();
        var piper = _piperVoices
            .Select(v => (v.DisplayName, v.ModelPath)).ToList();

        _allVoices = mode switch
        {
            TtsMode.Piper => [.. piper, .. online, .. offline],
            TtsMode.Offline => [.. offline, .. piper, .. online],
            _ => [.. online, .. piper, .. offline],
        };

        ComboVoice.ItemsSource = _allVoices.Select(v => v.DisplayName).ToList();
        if (_allVoices.Count > 0)
            ComboVoice.SelectedIndex = 0;
    }

    private void ComboTtsMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        int idx = ComboTtsMode.SelectedIndex;
        if (idx < 0 || idx >= TtsModes.Length) return;
        _selectedTtsMode = TtsModes[idx].Mode;

        UpdateVoiceList(_selectedTtsMode);

        // Обновляем статус
        if (LblModeStatus != null)
        {
            if (_selectedTtsMode == TtsMode.Piper)
            {
                if (_piperVoices.Count > 0)
                {
                    LblModeStatus.Text = $"Piper моделей: {_piperVoices.Count}. Нейросетевое качество, без интернета.";
                    LblModeStatus.Foreground = FindResource("SuccessBrush") as Brush;
                }
                else
                {
                    LblModeStatus.Text = "Piper не найден! Поместите piper.exe и модели (.onnx) в папку 'piper'.";
                    LblModeStatus.Foreground = FindResource("DangerBrush") as Brush;
                }
            }
            else if (_selectedTtsMode == TtsMode.Offline)
            {
                LblModeStatus.Text = _offlineVoices.Count > 0
                    ? $"Найдено SAPI-голосов: {_offlineVoices.Count}"
                    : "SAPI-голоса не найдены!";
                LblModeStatus.Foreground = _offlineVoices.Count > 0
                    ? FindResource("SuccessBrush") as Brush
                    : FindResource("DangerBrush") as Brush;
            }
            else if (_selectedTtsMode == TtsMode.Online)
            {
                LblModeStatus.Text = "Требуется интернет";
                LblModeStatus.Foreground = FindResource("TextSecondaryBrush") as Brush;
            }
            else
            {
                LblModeStatus.Text = "Автовыбор при старте";
                LblModeStatus.Foreground = FindResource("TextSecondaryBrush") as Brush;
            }
        }
    }

    // ── Обработчики шрифта лога ────────────────────────────────────────

    private void ComboLogFont_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ComboLogFont.SelectedItem is string fontName && TxtLog != null)
            TxtLog.FontFamily = new FontFamily(fontName);
    }

    private void ComboLogFontSize_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ComboLogFontSize.SelectedItem is string sizeStr && int.TryParse(sizeStr, out int size) && TxtLog != null)
            TxtLog.FontSize = size;
    }

    // ── Загрузка истории ─────────────────────────────────────────────

    private void LoadHistoryUI()
    {
        _history = HistoryManager.LoadHistory();
        _unfinished = HistoryManager.GetLastUnfinished();

        // Баннер «Продолжить»
        if (_unfinished != null)
        {
            string bookName = _unfinished.BookName ?? Path.GetFileNameWithoutExtension(_unfinished.InputFile ?? "");
            int done = _unfinished.DoneChapters;
            int total = _unfinished.TotalChapters;
            int pct = total > 0 ? done * 100 / total : 0;
            ResumeLabel.Text = $"Продолжить: {bookName}  ({done}/{total} — {pct}%)";
            ResumeCard.Visibility = Visibility.Visible;
        }

        // Список истории
        if (_history.Count > 0)
        {
            HistoryCard.Visibility = Visibility.Visible;
            ComboHistory.ItemsSource = _history.Select(FormatHistoryEntry).ToList();
        }
    }

    private static string FormatHistoryEntry(HistoryEntry e)
    {
        string name = e.BookName ?? "?";
        string status = e.Finished ? "готово" : $"{e.DoneChapters}/{e.TotalChapters}";
        return $"{name}  [{status}]  {e.LastUsed}";
    }

    private void LoadProject(HistoryEntry entry)
    {
        TxtInputFile.Text = entry.InputFile ?? "";
        TxtOutputDir.Text = entry.OutputDir ?? "";
        string? voice = entry.Voice;
        if (!string.IsNullOrEmpty(voice))
        {
            for (int i = 0; i < _allVoices.Count; i++)
            {
                if (_allVoices[i].ShortName == voice)
                {
                    ComboVoice.SelectedIndex = i;
                    break;
                }
            }
        }
    }

    // ── Обработчики кнопок ───────────────────────────────────────────

    private void BtnResume_Click(object sender, RoutedEventArgs e)
    {
        if (_unfinished != null) LoadProject(_unfinished);
    }

    private void ComboHistory_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        int idx = ComboHistory.SelectedIndex;
        if (idx >= 0 && idx < _history.Count)
            LoadProject(_history[idx]);
    }

    private void BtnBrowseInput_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog
        {
            Title = "Выберите текстовый файл",
            Filter = "Текстовые файлы (*.txt)|*.txt|Все файлы (*.*)|*.*"
        };
        if (dlg.ShowDialog() == true)
        {
            TxtInputFile.Text = dlg.FileName;
            if (string.IsNullOrEmpty(TxtOutputDir.Text))
            {
                string dir = Path.GetDirectoryName(dlg.FileName) ?? "";
                string name = Path.GetFileNameWithoutExtension(dlg.FileName);
                TxtOutputDir.Text = Path.Combine(dir, name + "_audio");
            }
            // Автоопределение языка и голоса
            AutoSelectVoice(dlg.FileName);
        }
    }

    private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "Выберите папку для сохранения" };
        if (dlg.ShowDialog() == true)
            TxtOutputDir.Text = dlg.FolderName;
    }

    private void BtnOpenFolder_Click(object sender, RoutedEventArgs e)
    {
        string dir = TxtOutputDir.Text.Trim();
        if (Directory.Exists(dir))
            Process.Start("explorer.exe", dir);
        else
            MessageBox.Show("Папка не найдена.", "Внимание", MessageBoxButton.OK, MessageBoxImage.Warning);
    }

    private void SliderSpeed_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        int val = (int)SliderSpeed.Value;
        if (LblSpeed != null)
            LblSpeed.Text = val >= 0 ? $"+{val}%" : $"{val}%";
    }

    // ── Автоопределение голоса ───────────────────────────────────────

    private void AutoSelectVoice(string filePath)
    {
        try
        {
            string enc = BookConverter.DetectEncoding(filePath);
            string sample = File.ReadAllText(filePath, System.Text.Encoding.GetEncoding(enc));
            if (sample.Length > 5000) sample = sample[..5000];
            string lang = BookConverter.DetectLanguage(sample);

            if (BookConverter.DefaultVoices.TryGetValue(lang, out string? defaultVoice))
            {
                for (int i = 0; i < _allVoices.Count; i++)
                {
                    if (_allVoices[i].ShortName == defaultVoice)
                    {
                        ComboVoice.SelectedIndex = i;
                        return;
                    }
                }
            }
        }
        catch { }
    }

    private string GetCurrentVoice()
    {
        int idx = -1;
        Dispatcher.Invoke(() => idx = ComboVoice.SelectedIndex);
        if (idx >= 0 && idx < _allVoices.Count)
            return _allVoices[idx].ShortName;
        return "";
    }

    // ── Пауза / Стоп ────────────────────────────────────────────────

    private void BtnPause_Click(object sender, RoutedEventArgs e)
    {
        if (_pauseToken == null) return;

        if (_pauseToken.IsPaused)
        {
            _pauseToken.Resume();
            BtnPause.Content = "Пауза";
            BtnPause.Background = FindResource("WarningBrush") as Brush;
        }
        else
        {
            _pauseToken.Pause();
            BtnPause.Content = "Продолжить";
            BtnPause.Background = FindResource("SuccessBrush") as Brush;
        }
    }

    private void BtnStop_Click(object sender, RoutedEventArgs e)
    {
        _cts?.Cancel();
    }

    // ── Запуск конвертации ───────────────────────────────────────────

    private void SetButtonsConverting(bool converting)
    {
        BtnStart.IsEnabled = !converting;
        BtnStop.IsEnabled = converting;
        BtnPause.IsEnabled = converting;
        if (!converting)
        {
            BtnPause.Content = "Пауза";
            BtnPause.Background = FindResource("WarningBrush") as Brush;
        }
    }

    private async void BtnStart_Click(object sender, RoutedEventArgs e)
    {
        string inputFile = TxtInputFile.Text.Trim();
        string outputDir = TxtOutputDir.Text.Trim();

        if (string.IsNullOrEmpty(inputFile))
        {
            MessageBox.Show("Выберите исходный файл.", "Внимание",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        if (!File.Exists(inputFile))
        {
            MessageBox.Show($"Файл не найден:\n{inputFile}", "Ошибка",
                MessageBoxButton.OK, MessageBoxImage.Error);
            return;
        }
        if (string.IsNullOrEmpty(outputDir))
        {
            MessageBox.Show("Укажите папку для сохранения.", "Внимание",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        int voiceIdx = ComboVoice.SelectedIndex;
        string voice = voiceIdx >= 0 && voiceIdx < _allVoices.Count
            ? _allVoices[voiceIdx].ShortName : "ru-RU-DmitryNeural";

        int speedVal = (int)SliderSpeed.Value;
        string speed = speedVal >= 0 ? $"+{speedVal}%" : $"{speedVal}%";

        string encoding = ComboEncoding.SelectedItem as string ?? "auto";
        bool merge = ChkMerge.IsChecked == true;
        bool noChapters = ChkNoChapters.IsChecked == true;
        bool deleteFragments = ChkDeleteFragments.IsChecked == true;

        // Очищаем лог
        TxtLog.Clear();
        SetProgress(0, 1);

        _cts = new CancellationTokenSource();
        _pauseToken = new PauseToken();
        _isConverting = true;
        SetButtonsConverting(true);

        var converter = new BookConverter();
        var opts = new ConversionOptions
        {
            InputFile = inputFile,
            OutputDir = outputDir,
            Voice = voice,
            Speed = speed,
            Merge = merge,
            NoChapters = noChapters,
            DeleteFragments = deleteFragments,
            Encoding = encoding,
            Log = msg => Dispatcher.BeginInvoke(() => AppendLog(msg)),
            Progress = (cur, total) => Dispatcher.BeginInvoke(() => SetProgress(cur, total)),
            TimeEstimate = text => Dispatcher.BeginInvoke(() => LblEta.Text = text),
            CancelToken = _cts.Token,
            PauseToken = _pauseToken,
            VoiceFunc = GetCurrentVoice,
            TtsMode = _selectedTtsMode,
        };

        ConversionResult? result = null;
        try
        {
            result = await Task.Run(() => converter.ConvertBookAsync(opts));
        }
        catch (OperationCanceledException)
        {
            AppendLog("\nОстановлено пользователем.");
        }
        catch (Exception ex)
        {
            AppendLog($"\nОшибка: {ex.Message}");
        }
        finally
        {
            _isConverting = false;
            SetButtonsConverting(false);
        }

        if (result != null)
            ShowCompletionDialog(result);
    }

    // ── Лог и прогресс ──────────────────────────────────────────────

    private void AppendLog(string message)
    {
        TxtLog.AppendText(message + "\n");
        TxtLog.ScrollToEnd();
    }

    private void SetProgress(int current, int total)
    {
        double frac = total > 0 ? (double)current / total : 0;
        int pct = (int)(frac * 100);

        // Ширина прогресс-бара
        double maxWidth = ProgressFill.Parent is FrameworkElement parent ? parent.ActualWidth : 0;
        if (maxWidth <= 0) maxWidth = 600;
        ProgressFill.Width = maxWidth * frac;

        LblPercent.Text = $"{pct}%";

        if (current >= total && total > 0)
        {
            ProgressFill.Background = FindResource("SuccessBrush") as Brush;
            LblPercent.Foreground = FindResource("SuccessBrush") as Brush;
            LblEta.Text = "";
        }
        else
        {
            ProgressFill.Background = FindResource("AccentBrush") as Brush;
            LblPercent.Foreground = FindResource("AccentBrush") as Brush;
        }
    }

    // ── Диалог завершения ────────────────────────────────────────────

    private void ShowCompletionDialog(ConversionResult result)
    {
        var dlg = new Window
        {
            Title = "Конвертация завершена",
            Width = 470,
            Height = 330,
            ResizeMode = ResizeMode.NoResize,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = FindResource("BgDarkBrush") as Brush,
        };

        var stack = new StackPanel { Margin = new Thickness(28, 24, 28, 20) };

        // Заголовок
        stack.Children.Add(new TextBlock
        {
            Text = "✔  Конвертация завершена!",
            FontSize = 18, FontWeight = FontWeights.Bold,
            Foreground = FindResource("SuccessBrush") as Brush,
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, 16),
        });

        // Информация
        var infoBorder = new Border
        {
            Background = FindResource("BgCardBrush") as Brush,
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(16, 12, 16, 12),
            Margin = new Thickness(0, 0, 0, 16),
        };

        var infoStack = new StackPanel();
        var lines = new List<(string Label, string Value)>
        {
            ("Книга:", result.BookName),
            ("Файлов создано:", result.TotalFiles.ToString()),
            ("Общий размер:", $"{result.TotalSizeMb} МБ"),
        };
        if (!string.IsNullOrEmpty(result.MergedFile))
            lines.Add(("Итоговый файл:", Path.GetFileName(result.MergedFile)));

        foreach (var (label, value) in lines)
        {
            var row = new Grid();
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            var lblBlock = new TextBlock
            {
                Text = label, FontSize = 13,
                Foreground = FindResource("TextSecondaryBrush") as Brush,
                Margin = new Thickness(0, 2, 0, 2),
            };
            Grid.SetColumn(lblBlock, 0);

            var valBlock = new TextBlock
            {
                Text = value, FontSize = 13, FontWeight = FontWeights.Bold,
                Foreground = FindResource("TextPrimaryBrush") as Brush,
                HorizontalAlignment = HorizontalAlignment.Right,
                Margin = new Thickness(0, 2, 0, 2),
            };
            Grid.SetColumn(valBlock, 1);

            row.Children.Add(lblBlock);
            row.Children.Add(valBlock);
            infoStack.Children.Add(row);
        }
        infoBorder.Child = infoStack;
        stack.Children.Add(infoBorder);

        // Кнопки
        var btnPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Center };

        if (!string.IsNullOrEmpty(result.MergedFile) && File.Exists(result.MergedFile))
        {
            string mergedFile = result.MergedFile;
            var btnOpen = CreateDialogButton("▶  Открыть аудиофайл", "#6C63FF");
            btnOpen.Click += (_, _) =>
            {
                Process.Start(new ProcessStartInfo(mergedFile) { UseShellExecute = true });
                dlg.Close();
            };
            btnPanel.Children.Add(btnOpen);
        }

        if (Directory.Exists(result.OutputDir))
        {
            string outDir = result.OutputDir;
            var btnFolder = CreateDialogButton("📁  Открыть папку", "#E67E22");
            btnFolder.Margin = new Thickness(8, 0, 0, 0);
            btnFolder.Click += (_, _) =>
            {
                Process.Start("explorer.exe", outDir);
                dlg.Close();
            };
            btnPanel.Children.Add(btnFolder);
        }

        var btnClose = CreateDialogButton("Закрыть", "#0F3460");
        btnClose.Foreground = FindResource("TextSecondaryBrush") as Brush;
        btnClose.FontWeight = FontWeights.Normal;
        btnClose.Margin = new Thickness(8, 0, 0, 0);
        btnClose.Click += (_, _) => dlg.Close();
        btnPanel.Children.Add(btnClose);

        stack.Children.Add(btnPanel);
        dlg.Content = stack;
        dlg.ShowDialog();
    }

    private static Button CreateDialogButton(string text, string bgColor)
    {
        var btn = new Button
        {
            Content = text,
            Height = 38,
            Padding = new Thickness(16, 0, 16, 0),
            Foreground = Brushes.White,
            FontWeight = FontWeights.Bold,
            FontSize = 13,
            Cursor = System.Windows.Input.Cursors.Hand,
            BorderThickness = new Thickness(0),
        };

        var color = (Color)ColorConverter.ConvertFromString(bgColor);
        var template = new ControlTemplate(typeof(Button));
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.BackgroundProperty, new SolidColorBrush(color));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(10));
        border.SetValue(Border.PaddingProperty, new Thickness(16, 8, 16, 8));
        border.AppendChild(new FrameworkElementFactory(typeof(ContentPresenter)));
        template.VisualTree = border;
        btn.Template = template;

        return btn;
    }
}
