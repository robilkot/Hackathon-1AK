using Avalonia.Controls;
using ConveyorCV_frontend.ViewModels;

namespace ConveyorCV_frontend.Views;

public partial class SettingsWindow : Window
{
    private static SettingsViewModel? _vm;

    public SettingsWindow()
    {
        InitializeComponent();

        _vm ??= new SettingsViewModel();
        DataContext = _vm;
    }
}
