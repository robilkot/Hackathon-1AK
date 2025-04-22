using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class SizeViewModel : ViewModelBase
    {
        private double _height;
        public double Height
        {
            get => _height;
            set => this.RaiseAndSetIfChanged(ref _height, value);
        }

        private double _width;
        public double Width
        {
            get => _width;
            set => this.RaiseAndSetIfChanged(ref _width, value);
        }

        public SizeViewModel(double width, double height)
        {
            Height = height;
            Width = width;
        }
    }
}
