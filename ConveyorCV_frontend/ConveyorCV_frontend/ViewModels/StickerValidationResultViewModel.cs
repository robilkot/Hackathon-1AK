using Avalonia.Media.Imaging;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerValidationResultViewModel : ViewModelBase
    {
        private Bitmap? _image;
        public Bitmap? Image
        {
            get => _image;
            set => this.RaiseAndSetIfChanged(ref _image, value);
        }

        private bool _stickerPresent;
        public bool StickerPresent
        {
            get => _stickerPresent;
            set => this.RaiseAndSetIfChanged(ref _stickerPresent, value);
        }

        private bool? _stickerMatchesDesign;
        public bool? StickerMatchesDesign
        {
            get => _stickerMatchesDesign;
            set => this.RaiseAndSetIfChanged(ref _stickerMatchesDesign, value);
        }

        private PointViewModel? _stickerLocation = new(300f, 200f);
        public PointViewModel? StickerLocation
        {
            get => _stickerLocation;
            set => this.RaiseAndSetIfChanged(ref _stickerLocation, value);
        }

        private SizeViewModel _stickerSize = new(400f, 200f);
        public SizeViewModel StickerSize
        {
            get => _stickerSize;
            set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
        }

        private double? _rotation = 5;
        public double? Rotation
        {
            get => _rotation;
            set => this.RaiseAndSetIfChanged(ref _rotation, value);
        }
    }
}
