using System;
using System.Collections.Generic;
using System.Reactive;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Services;
using ConveyorCV_frontend.ViewModels;
using ReactiveUI;

public class MainViewModel : ViewModelBase
{
    private readonly WebSocketService _webSocketService;
    private Bitmap _rawImage;
    private string _status = "Отключено";
    private bool _isStreaming = false;

    private StickerParametersViewModel _stickerParameters;
    public StickerParametersViewModel StickerParameters
    {
        get => _stickerParameters;
        set => this.RaiseAndSetIfChanged(ref _stickerParameters, value);
    }

    private StickerValidationResultViewModel _validationResult;
    public StickerValidationResultViewModel ValidationResult
    {
        get => _validationResult;
        set => this.RaiseAndSetIfChanged(ref _validationResult, value);
    }

    public ReactiveCommand<Unit, Unit> StartStreamCommand { get; }
    public ReactiveCommand<Unit, Unit> StopStreamCommand { get; }

    public Bitmap RawImage
    {
        get => _rawImage;
        private set => this.RaiseAndSetIfChanged(ref _rawImage, value);
    }

    public string Status
    {
        get => _status;
        set => this.RaiseAndSetIfChanged(ref _status, value);
    }

    public bool IsStreaming
    {
        get => _isStreaming;
        private set => this.RaiseAndSetIfChanged(ref _isStreaming, value);
    }

    public MainViewModel()
    {
        _webSocketService = new WebSocketService();
        _webSocketService.ImageReceived += OnImageReceived;
        _webSocketService.ConnectionClosed += OnConnectionClosed;
        _webSocketService.ErrorOccurred += OnErrorOccurred;

        StickerParameters = new StickerParametersViewModel();
        ValidationResult = new StickerValidationResultViewModel(_webSocketService);
        
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
            
            // Let validation view handle its own connections
            await ValidationResult.ConnectAsync();
            
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
            
            // Let validation view handle its own disconnections
            await ValidationResult.DisconnectAsync();
            
            IsStreaming = false;
            Status = "Трансляция остановлена";
        }
        catch (Exception ex) {
            Status = $"Ошибка: {ex.Message}";
        }
    }

    private void OnImageReceived(string streamType, Bitmap image)
    {
        if (streamType == "raw")
        {
            RawImage = image;
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