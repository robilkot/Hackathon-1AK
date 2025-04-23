using System;
using System.Collections.Generic;
using System.Reactive;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Services;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class StreamViewModel : ViewModelBase
    {
        private readonly WebSocketService _webSocketService;
        private Bitmap _rawImage;
        private Bitmap _validationImage;
        private string _status = "Отключено";
        private bool _isStreaming = false;

        public ReactiveCommand<Unit, Unit> StartStreamCommand { get; }
        public ReactiveCommand<Unit, Unit> StopStreamCommand { get; }
        
        private StickerValidationResultViewModel _validationResultViewModel;
        public StickerValidationResultViewModel ValidationResultViewModel
        {
            get => _validationResultViewModel;
            set => this.RaiseAndSetIfChanged(ref _validationResultViewModel, value);
        }

        public Bitmap RawImage
        {
            get => _rawImage;
            private set => this.RaiseAndSetIfChanged(ref _rawImage, value);
        }

        public Bitmap ValidationImage
        {
            get => _validationImage;
            private set => this.RaiseAndSetIfChanged(ref _validationImage, value);
        }

        public string Status
        {
            get => _status;
            private set => this.RaiseAndSetIfChanged(ref _status, value);
        }

        public bool IsStreaming
        {
            get => _isStreaming;
            private set => this.RaiseAndSetIfChanged(ref _isStreaming, value);
        }

        public StreamViewModel(StickerValidationResultViewModel validationResultViewModel)
        {
            _validationResultViewModel = validationResultViewModel;
            _webSocketService = new WebSocketService();
            _webSocketService.ImageReceived += OnImageReceived;
            _webSocketService.EventReceived += OnEventReceived;
            _webSocketService.ConnectionClosed += OnConnectionClosed;
            _webSocketService.ErrorOccurred += OnErrorOccurred;

            StartStreamCommand = ReactiveCommand.CreateFromTask(StartStreamAsync);
            StopStreamCommand = ReactiveCommand.CreateFromTask(StopStreamAsync);
        }

        private async Task StartStreamAsync()
        {
            try {
                if (IsStreaming)
                    return;

                Status = "Подключение...";
                
                await _webSocketService.ConnectAsync("/ws/raw", "raw");
                await _webSocketService.ConnectAsync("/ws/validation", "validation");
                await _webSocketService.ConnectAsync("/ws/events", "events");
                
                Status = "Запуск трансляции...";
                await _webSocketService.StartStreamAsync();
                IsStreaming = true;
                Status = "Трансляция";
            }
            catch (Exception ex) {
                Status = $"Ошибка: {ex.Message}";
            }
        }

        private async Task StopStreamAsync()
        {
            try {
                if (!IsStreaming)
                    return;

                Status = "Остановка трансляции...";
                await _webSocketService.StopStreamAsync();
                
                await _webSocketService.DisconnectAsync("raw");
                await _webSocketService.DisconnectAsync("validation");
                await _webSocketService.DisconnectAsync("events");
                
                IsStreaming = false;
                Status = "Трансляция остановлена";
            }
            catch (Exception ex) {
                Status = $"Ошибка: {ex.Message}";
            }
        }

        private void OnImageReceived(string streamType, Bitmap image)
        {
            switch (streamType)
            {
                case "raw":
                    RawImage = image;
                    break;
                case "validation":
                    ValidationImage = image;
                    ValidationResultViewModel.Image = image;
                    break;
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
                        
                    ValidationResultViewModel.StickerPresent = parsedValue;
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
                        
                    ValidationResultViewModel.StickerMatchesDesign = parsedValue;
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

                    ValidationResultViewModel.StickerLocation = new PointViewModel(x, y);
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

                    ValidationResultViewModel.StickerSize = new SizeViewModel(width, height);
                }

                // Process rotation if available
                if (data.TryGetValue("rotation", out var rotation))
                {
                    double rotationValue = 0;
                    if (rotation is double doubleVal)
                        rotationValue = doubleVal;
                    else if (rotation != null)
                        rotationValue = Convert.ToDouble(rotation);
                        
                    ValidationResultViewModel.Rotation = rotationValue;
                }
                
            }
        }
    }
    catch (Exception ex)
    {
        Status = $"Ошибка обработки события: {ex.Message}";
    }
}

        private void OnConnectionClosed(string streamType)
        {
            if (streamType == "raw")
            {
                Status = "Соединение с трансляцией потеряно";
                IsStreaming = false;
            }
        }

        private void OnErrorOccurred(string streamType, Exception ex)
        {
            Status = $"Ошибка в {streamType}: {ex.Message}";
        }
    }
}