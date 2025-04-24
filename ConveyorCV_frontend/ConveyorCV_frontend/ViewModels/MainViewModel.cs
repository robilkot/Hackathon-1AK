using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ConveyorCV_frontend.ViewModels;
using ReactiveUI;
using System;
using System.Diagnostics;
using System.Reactive;
using System.Threading.Tasks;

public class MainViewModel : ViewModelBase
{
    private readonly WebSocketService _webSocketService;

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

    private Bitmap _rawImage;
    public Bitmap RawImage
    {
        get => _rawImage;
        private set => this.RaiseAndSetIfChanged(ref _rawImage, value);
    }

    private StreamStatus _status = StreamStatus.Disconnected;
    public StreamStatus Status
    {
        get => _status;
        set => this.RaiseAndSetIfChanged(ref _status, value);
    }

    private bool _isStreaming = false;
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
        try
        {
            if (IsStreaming)
                return;

            Status = StreamStatus.Connecting;
            await _webSocketService.ConnectAsync("/ws/raw", "raw");

            // todo review. seems shit
            // Let validation view handle its own connections
            await ValidationResult.ConnectAsync();

            Status = StreamStatus.Starting;
            await _webSocketService.StartStreamAsync();
            IsStreaming = true;
            Status = StreamStatus.Running;
        }
        catch (Exception ex)
        {
            Status = StreamStatus.Error;
            Console.WriteLine("Stream exception: ", ex.Message);
        }
    }

    private async Task StopStreamAsync()
    {
        try
        {
            if (!IsStreaming)
                return;

            Status = StreamStatus.Stopping;
            await _webSocketService.StopStreamAsync();

            await _webSocketService.DisconnectAsync("raw");

            // Let validation view handle its own disconnections
            await ValidationResult.DisconnectAsync();

            IsStreaming = false;
            Status = StreamStatus.Disconnected;
        }
        catch (Exception ex)
        {
            Status = StreamStatus.Error;
            Console.WriteLine("Stream exception: ", ex.Message);
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
            Status = StreamStatus.LostConnection;
            IsStreaming = false;
        }
    }

    private void OnErrorOccurred(string streamType, Exception ex)
    {
        Status = StreamStatus.Error;
        Console.WriteLine("Stream exception: ", ex.Message);
    }
}