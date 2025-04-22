using Avalonia.Media.Imaging;
using ReactiveUI;
using System.Drawing;
using System.Reactive.Linq;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerParametersViewModel : ViewModelBase
    {
        private Bitmap? _image;
        public Bitmap? Image
        {
            get => _image;
            set => this.RaiseAndSetIfChanged(ref _image, value);
        }

        private PointF? _center = new(300f, 200f);
        public PointF? Center
        {
            get => _center;
            set => this.RaiseAndSetIfChanged(ref _center, value);
        }

        private SizeViewModel _stickerSize = new(400f, 200f);
        public SizeViewModel StickerSize
        {
            get => _stickerSize;
            set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
        }

        private double _rotation = 0;
        public double Rotation
        {
            get => _rotation;
            set => this.RaiseAndSetIfChanged(ref _rotation, value);
        }

        private SizeViewModel _accSize = new(600f, 400f);
        public SizeViewModel AccSize
        {
            get => _accSize;
            set => this.RaiseAndSetIfChanged(ref _accSize, value);
        }
    }
}
