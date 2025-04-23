using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Services;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerValidationResultViewModel : ViewModelBase
    {
        private readonly WebSocketService _webSocketService;
        private Bitmap? _image;
        private bool _stickerPresent;
        private bool? _stickerMatchesDesign;
        private PointViewModel? _stickerLocation = new(300f, 200f);
        private SizeViewModel _stickerSize = new(400f, 200f);
        private double? _rotation = 5;
        private string _validationStatus = "";

        public Bitmap? Image
        {
            get => _image;
            set => this.RaiseAndSetIfChanged(ref _image, value);
        }

        public bool StickerPresent
        {
            get => _stickerPresent;
            set => this.RaiseAndSetIfChanged(ref _stickerPresent, value);
        }

        public bool? StickerMatchesDesign
        {
            get => _stickerMatchesDesign;
            set => this.RaiseAndSetIfChanged(ref _stickerMatchesDesign, value);
        }

        public PointViewModel? StickerLocation
        {
            get => _stickerLocation;
            set => this.RaiseAndSetIfChanged(ref _stickerLocation, value);
        }

        public SizeViewModel StickerSize
        {
            get => _stickerSize;
            set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
        }

        public double? Rotation
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
            _webSocketService = webSocketService;
            _webSocketService.ImageReceived += OnImageReceived;
            _webSocketService.EventReceived += OnEventReceived;
        }

        public async Task ConnectAsync()
        {
            await _webSocketService.ConnectAsync("/ws/validation", "validation");
            await _webSocketService.ConnectAsync("/ws/events", "events");
        }

        public async Task DisconnectAsync()
        {
            await _webSocketService.DisconnectAsync("validation");
            await _webSocketService.DisconnectAsync("events");
        }

        private void OnImageReceived(string streamType, Bitmap image)
        {
            if (streamType == "validation")
            {
                Image = image;
            }
        }

        private void OnEventReceived(string streamType, object eventData)
        {
            try
            {
                if (streamType == "events" && eventData is Dictionary<string, object> data)
                {
                    if (data.TryGetValue("type", out var type) && type.ToString() == "validation_result")
                    {
                        // More robust handling of sticker_present
                        if (data.TryGetValue("sticker_present", out var stickerPresent))
                        {
                            bool parsedValue = false;
                            if (stickerPresent is bool boolVal)
                                parsedValue = boolVal;
                            else if (stickerPresent is JsonElement jsonElement)
                                parsedValue = jsonElement.GetBoolean();
                            else if (stickerPresent != null)
                                parsedValue = Convert.ToBoolean(stickerPresent);
                                
                            StickerPresent = parsedValue;
                        }

                        // More robust handling of sticker_matches_design
                        if (data.TryGetValue("sticker_matches_design", out var matchesDesign))
                        {
                            bool parsedValue = false;
                            if (matchesDesign is bool boolVal)
                                parsedValue = boolVal;
                            else if (matchesDesign is JsonElement jsonElement)
                                parsedValue = jsonElement.GetBoolean();
                            else if (matchesDesign != null)
                                parsedValue = Convert.ToBoolean(matchesDesign);
                                
                            StickerMatchesDesign = parsedValue;
                        }

                        // Process position if available
                        if (data.TryGetValue("position", out var position) &&
                            position is Dictionary<string, object> posData)
                        {
                            double x = 0, y = 0;
                            if (posData.TryGetValue("x", out var xVal))
                                x = Convert.ToDouble(xVal);
                            if (posData.TryGetValue("y", out var yVal))
                                y = Convert.ToDouble(yVal);

                            StickerLocation = new PointViewModel(x, y);
                        }

                        // Process size if available
                        if (data.TryGetValue("size", out var size) && 
                            size is Dictionary<string, object> sizeData)
                        {
                            double width = 0, height = 0;
                            if (sizeData.TryGetValue("width", out var widthVal))
                                width = Convert.ToDouble(widthVal);
                            if (sizeData.TryGetValue("height", out var heightVal))
                                height = Convert.ToDouble(heightVal);

                            StickerSize = new SizeViewModel(width, height);
                        }

                        // Process rotation if available
                        if (data.TryGetValue("rotation", out var rotation))
                        {
                            double rotationValue = 0;
                            if (rotation is double doubleVal)
                                rotationValue = doubleVal;
                            else if (rotation != null)
                                rotationValue = Convert.ToDouble(rotation);
                                
                            Rotation = rotationValue;
                        }
                        
                        // Update validation status to confirm changes were processed
                        ValidationStatus = $"Наклейка: {(StickerPresent ? "присутствует" : "отсутствует")}, " +
                                        $"Соответствие: {(StickerMatchesDesign == true ? "да" : "нет")}";
                    }
                }
            }
            catch (Exception ex)
            {
                ValidationStatus = $"Ошибка обработки события: {ex.Message}";
            }
        }
    }
}