using System;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerValidationResultViewModel : ViewModelBase
    {
        private readonly ValidationService _validationService;
        private Bitmap _image;
        private bool _stickerPresent;
        private bool _stickerMatchesDesign;
        private PointViewModel _stickerLocation = new(300f, 200f);
        private SizeViewModel _stickerSize = new(400f, 200f);
        private double _rotation = 5;
        private string _validationStatus = "";

        public Bitmap Image
        {
            get => _image;
            set => this.RaiseAndSetIfChanged(ref _image, value);
        }

        public bool StickerPresent
        {
            get => _stickerPresent;
            set => this.RaiseAndSetIfChanged(ref _stickerPresent, value);
        }

        public bool StickerMatchesDesign
        {
            get => _stickerMatchesDesign;
            set => this.RaiseAndSetIfChanged(ref _stickerMatchesDesign, value);
        }

        public PointViewModel StickerLocation
        {
            get => _stickerLocation;
            set => this.RaiseAndSetIfChanged(ref _stickerLocation, value);
        }

        public SizeViewModel StickerSize
        {
            get => _stickerSize;
            set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
        }

        public double Rotation
        {
            get => _rotation;
            set => this.RaiseAndSetIfChanged(ref _rotation, value);
        }

        public string ValidationStatus
        {
            get => _validationStatus;
            set => this.RaiseAndSetIfChanged(ref _validationStatus, value);
        }

        public StickerValidationResultViewModel(WebSocketService webSocketService)
        {
            _validationService = new ValidationService(webSocketService);
            _validationService.ImageReceived += OnImageReceived;
            _validationService.ValidationResultReceived += OnValidationResultReceived;
            _validationService.ErrorOccurred += OnErrorOccurred;
        }

        public async Task ConnectAsync()
        {
            await _validationService.ConnectAsync();
        }

        public async Task DisconnectAsync()
        {
            await _validationService.DisconnectAsync();
        }

        private void OnImageReceived(Bitmap image)
        {
            Image = image;
        }

        private void OnValidationResultReceived(ValidationResultDTO result)
        {
            StickerPresent = result.StickerPresent;
            StickerMatchesDesign = result.StickerMatchesDesign;
            
            // Update position if available
            if (result.Position != null)
            {
                double x = 0, y = 0;
                if (result.Position.TryGetValue("x", out var xVal))
                    x = Convert.ToDouble(xVal);
                if (result.Position.TryGetValue("y", out var yVal))
                    y = Convert.ToDouble(yVal);
                
                StickerLocation = new PointViewModel(x, y);
            }

            // Update size if available
            if (result.Size != null)
            {
                double width = 0, height = 0;
                if (result.Size.TryGetValue("width", out var widthVal))
                    width = Convert.ToDouble(widthVal);
                if (result.Size.TryGetValue("height", out var heightVal))
                    height = Convert.ToDouble(heightVal);
                
                StickerSize = new SizeViewModel(width, height);
            }

            // Update rotation if available
            if (result.Rotation.HasValue)
            {
                Rotation = result.Rotation.Value;
            }

            // Update validation status
            ValidationStatus = $"Наклейка: {(StickerPresent ? "присутствует" : "отсутствует")}, " +
                            $"Соответствие: {(StickerMatchesDesign ? "да" : "нет")}";
        }

        private void OnErrorOccurred(string message)
        {
            ValidationStatus = $"Ошибка: {message}";
        }
    }
}