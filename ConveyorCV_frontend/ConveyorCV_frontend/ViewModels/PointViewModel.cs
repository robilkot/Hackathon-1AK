using ReactiveUI;
using System.Drawing;

namespace ConveyorCV_frontend.ViewModels
{
    public class PointViewModel : ViewModelBase
    {
        private double _y;
        public double Y
        {
            get => _y;
            set => this.RaiseAndSetIfChanged(ref _y, value);
        }

        private double _x;
        public double X
        {
            get => _x;
            set => this.RaiseAndSetIfChanged(ref _x, value);
        }

        public PointViewModel(double x, double y)
        {
            Y = y;
            X = x;
        }
        public PointViewModel(PointF point)
        {
            Y = point.Y;
            X = point.X;
        }
    }
}
