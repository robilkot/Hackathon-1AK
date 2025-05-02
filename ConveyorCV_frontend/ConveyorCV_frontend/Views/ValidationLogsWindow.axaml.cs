using Avalonia.Controls;
using ConveyorCV_frontend.ViewModels;

namespace ConveyorCV_frontend.Views;

public partial class ValidationLogsWindow : Window
{
    private static ValidationLogsViewModel? _vm;

    public ValidationLogsWindow()
    {
        InitializeComponent();

        _vm ??= new ValidationLogsViewModel();
        DataContext = _vm;
    }
}
