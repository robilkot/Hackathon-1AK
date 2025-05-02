using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ConveyorCV_frontend.ViewModels;
using ReactiveUI;
using System;
using System.Diagnostics;
using System.IO;
using System.Reactive;
using System.Reactive.Linq;
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
    
    public MainViewModel()
    {
        _webSocketService = new WebSocketService();
        _webSocketService.MessageReceived += _webSocketService_MessageReceived;
        _webSocketService.ConnectionClosed += OnConnectionClosed;
        _webSocketService.ErrorOccurred += OnErrorOccurred;

        StickerParameters = new StickerParametersViewModel();
        _ = StickerParameters.InitializeAsync();
        ValidationResult = new StickerValidationResultViewModel(_webSocketService);

        var canStart = this.WhenAnyValue(x => x.Status).Select(status => status is StreamStatus.Disconnected or StreamStatus.LostConnection or StreamStatus.Error);
        var canStop = canStart.Select(value => !value);
        StartStreamCommand = ReactiveCommand.CreateFromTask(StartStreamAsync, canStart);
        StopStreamCommand = ReactiveCommand.CreateFromTask(StopStreamAsync, canStop);
    }

    private void _webSocketService_MessageReceived(StreamingMessage obj)
    {
        if (obj.Type != StreamingMessageType.RAW || obj.Content is not ImageStreamingMessageContent imageContent)
            return;

        var bytes = imageContent.ToImageBytes();

        using var stream = new MemoryStream(bytes);

        RawImage = new(stream);
    }

    private async Task StartStreamAsync()
    {
        try
        {
            Status = StreamStatus.Connecting;
            await _webSocketService.ConnectAsync();
            Status = StreamStatus.Starting;
            await _webSocketService.StartStreamAsync();
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
            Status = StreamStatus.Stopping;
            await _webSocketService.StopStreamAsync();

            await _webSocketService.DisconnectAsync();

            Status = StreamStatus.Disconnected;
        }
        catch (Exception ex)
        {
            Status = StreamStatus.Error;
            Debug.WriteLine("Stream exception: ", ex.Message);
        }
    }

    private void OnConnectionClosed()
    {
        Status = StreamStatus.LostConnection;
    }

    private void OnErrorOccurred(Exception ex)
    {
        Status = StreamStatus.Error;
        Debug.WriteLine("Stream exception: ", ex.Message);
        
        throw ex;
    }
}
