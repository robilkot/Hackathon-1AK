using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;

namespace ConveyorCV_frontend.Views;

public partial class MainView : UserControl
{
    private ValidationLogsWindow? _validationLogsWindow = null;
    private SettingsWindow? _settingsWindow = null;

    public MainView()
    {
        InitializeComponent();

        AttachedToVisualTree += (_, e) =>
        {
            if (App.Current.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop 
            && desktop.MainWindow is not null)
            {
                desktop.MainWindow.Closed += (_, e) =>
                {
                    _validationLogsWindow?.Close();
                    _settingsWindow?.Close();
                };
            }
        };
    }

    private void MenuItem_Click(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        _validationLogsWindow ??= new ValidationLogsWindow();

        _validationLogsWindow.Closed += (_, e) => _validationLogsWindow = null;
        _validationLogsWindow.Show();
        _validationLogsWindow.Activate();
    }

    private void MenuItem_Click_1(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        _settingsWindow ??= new SettingsWindow();

        _settingsWindow.Closed += (_, e) => _settingsWindow = null;
        _settingsWindow.Show();
        _settingsWindow.Activate();
    }
}