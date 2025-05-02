using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class SettingsViewModel : ViewModelBase
    {
        private double _y;
        public double Y
        {
            get => _y;
            set => this.RaiseAndSetIfChanged(ref _y, value);
        }

        public SettingsViewModel()
        {
            
        }
    }
}
