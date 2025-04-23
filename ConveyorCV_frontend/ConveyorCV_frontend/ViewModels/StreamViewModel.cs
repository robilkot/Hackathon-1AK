using System;
using System.Collections.Generic;
using System.Reactive;
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
                
                // Connect to each stream
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
                
                // Disconnect from all streams
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
            if (streamType == "events" && eventData is Dictionary<string, object> data)
            {
                // Handle validation results
                if (data.TryGetValue("type", out var type) && type.ToString() == "validation_result")
                {
                    // Update validation result in the associated view model
                    if (data.TryGetValue("sticker_present", out var stickerPresent) &&
                        stickerPresent is bool presentBool)
                    {
                        ValidationResultViewModel.StickerPresent = presentBool;
                    }

                    if (data.TryGetValue("sticker_matches_design", out var matchesDesign) &&
                        matchesDesign is bool matchesBool)
                    {
                        ValidationResultViewModel.StickerMatchesDesign = matchesBool;
                    }

                    // Update position if available
                    if (data.TryGetValue("position", out var position) &&
                        position is Dictionary<string, object> posData)
                    {
                        double x = 0, y = 0;
                        if (posData.TryGetValue("x", out var xVal) && xVal is double xDouble)
                            x = xDouble;
                        if (posData.TryGetValue("y", out var yVal) && yVal is double yDouble)
                            y = yDouble;

                        ValidationResultViewModel.StickerLocation = new PointViewModel(x, y);
                    }

                    // Update size if available
                    if (data.TryGetValue("size", out var size) && size is Dictionary<string, object> sizeData)
                    {
                        double width = 0, height = 0;
                        if (sizeData.TryGetValue("width", out var widthVal) && widthVal is double widthDouble)
                            width = widthDouble;
                        if (sizeData.TryGetValue("height", out var heightVal) && heightVal is double heightDouble)
                            height = heightDouble;

                        ValidationResultViewModel.StickerSize = new SizeViewModel(width, height);
                    }

                    // Update rotation if available
                    if (data.TryGetValue("rotation", out var rotation) && rotation is double rotationDouble)
                    {
                        ValidationResultViewModel.Rotation = rotationDouble;
                    }

                    // The validation image should already be updated via OnImageReceived
                    // but if it's included in this event, we could update it here as well
                }
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