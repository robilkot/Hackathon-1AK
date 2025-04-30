using Avalonia.Controls;
using Avalonia.Markup.Xaml;

namespace ConveyorCV_frontend.Views
{
    public partial class ValidationLogsView : UserControl
    {
        public ValidationLogsView()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }
    }
}