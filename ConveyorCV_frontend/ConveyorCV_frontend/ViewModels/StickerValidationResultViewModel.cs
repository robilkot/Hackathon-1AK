using System;
using System.ComponentModel;
using System.Diagnostics;
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
        private StickerValidationResultDTO? _lastResult;
        public StickerValidationResultDTO? LastResult
        {
            get => _lastResult;
            set
            {
                this.RaiseAndSetIfChanged(ref _lastResult, value);
        
                if (value != null)
                {
                    StickerPresent = value.StickerPresent ?? false;
                    StickerMatchesDesign = value.StickerMatchesDesign;
                    StickerLocation = value.StickerPosition.HasValue ? new(value.StickerPosition.Value) : null;
                    StickerSize = value.StickerSize.HasValue ? new(value.StickerSize.Value) : null;
                    Rotation = value.StickerRotation;
                    SeqNumber = value.SeqNumber ?? 0;
                    DetectionTime = value.Timestamp ?? DateTimeOffset.Now;
            
                    // Handle image safely
                    if (value.Image != null && value.Image.Length > 0)
                    {
                        try
                        {
                            using var ms = new MemoryStream(value.Image);
                            Image = new Bitmap(ms);
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine($"Error loading image: {ex.Message}");
                        }
                    }
                }
            }
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
            webSocketService.MessageReceived += WebSocketService_MessageReceived;
        }

        private void WebSocketService_MessageReceived(StreamingMessage obj)
        {
            if (obj.Content is not ValidationStreamingMessageContent validationMessage)
                return;
            
            LastResult = validationMessage.ValidationResult;
        }

        public StickerValidationResultViewModel()
        {
            if (!Design.IsDesignMode)
            {
                throw new NotSupportedException();
            }

            LastResult = new([], new(), 0, true, false, new(), new(), 5);
        }
    }
}