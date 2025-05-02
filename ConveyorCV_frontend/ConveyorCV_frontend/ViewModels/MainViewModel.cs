using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia;
using Avalonia.Media.Imaging;
using Avalonia.Notification;
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
    public INotificationMessageManager Manager { get; } = new NotificationMessageManager();

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
        _webSocketService.ErrorOccurred += OnErrorOccurred;
        _webSocketService.ConnectionClosed += _webSocketService_ConnectionClosed;

        StickerParameters = new StickerParametersViewModel()
        {
            Manager = Manager
        };
        _ = StickerParameters.InitializeAsync();
        ValidationResult = new StickerValidationResultViewModel(_webSocketService);

        //var canStart = this.WhenAnyValue(x => x.Status).Select(status => status is StreamStatus.Disconnected or StreamStatus.LostConnection or StreamStatus.Error);
        //var canStop = canStart.Select(value => !value);
        StartStreamCommand = ReactiveCommand.CreateFromTask(StartStreamAsync);
        StopStreamCommand = ReactiveCommand.CreateFromTask(StopStreamAsync);
    }

    private void _webSocketService_ConnectionClosed()
    {
        Status = StreamStatus.Disconnected;
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
            OnErrorOccurred(ex);
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
            OnErrorOccurred(ex);
        }
    }

    private void OnErrorOccurred(Exception ex)
    {
        Status = StreamStatus.Disconnected;
        Debug.WriteLine("Stream exception: ", ex.Message);

        Manager.Error("Ошибка соединения", ex.Message);
    }
}
