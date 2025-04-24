using System;
using System.IO;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerValidationResultViewModel : ViewModelBase
    {
        private readonly ValidationService _validationService;

        private StickerValidationResult? _lastResult;
        public StickerValidationResult? LastResult
        {
            get => _lastResult;
            set => this.RaiseAndSetIfChanged(ref _lastResult, value);
        }

        private Bitmap _image;
        public Bitmap Image
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

        private SizeViewModel? _stickerSize = new(400f, 200f);
        public SizeViewModel? StickerSize
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

        private int _seqNumber = 42;
        public int SeqNumber
        {
            get => _seqNumber;
            set => this.RaiseAndSetIfChanged(ref _seqNumber, value);
        }

        private DateTimeOffset _detectionTime = DateTimeOffset.Now;
        public DateTimeOffset DetectionTime
        {
            get => _detectionTime;
            set => this.RaiseAndSetIfChanged(ref _detectionTime, value);
        }


        public StickerValidationResultViewModel(WebSocketService webSocketService)
        {
            _validationService = new ValidationService(webSocketService);
            _validationService.ValidationResultReceived += OnValidationResultReceived;
        }

        public StickerValidationResultViewModel()
        {
            if (!Design.IsDesignMode)
            {
                throw new NotSupportedException();
            }

            LastResult = new([], new(), 0, true, false, new(), new(), 5);
        }

        public async Task ConnectAsync()
        {
            await _validationService.ConnectAsync();
        }

        public async Task DisconnectAsync()
        {
            await _validationService.DisconnectAsync();
        }

        private void OnValidationResultReceived(StickerValidationResult result)
        {
            using (var ms = new MemoryStream(result.Image))
            {
                var bitmap = new Bitmap(ms);
                if (bitmap != null)
                {
                    Image = bitmap;
                }
            }

            StickerPresent = result.StickerPresent;
            StickerMatchesDesign = result.StickerMatchesDesign;
            StickerLocation = result.StickerLocation.HasValue ? new(result.StickerLocation.Value) : null;
            StickerSize = new(result.StickerSize);
            Rotation = result.Rotation;
            SeqNumber = result.SeqNumber;
            DetectionTime = result.Timestamp;

            LastResult = result;
        }
    }
}