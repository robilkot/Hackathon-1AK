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
using System.Threading.Tasks;

public class MainViewModel : ViewModelBase
{
    public INotificationMessageManager Manager { get; } = new NotificationMessageManager();

    private readonly WebSocketService _webSocketService;
    private readonly ConveyorPhotoService _conveyorPhotoService;
    public ReactiveCommand<Unit, Unit> SaveEmptyConveyorPhotoCommand { get; }

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
    private Bitmap _shapeImage;
    public Bitmap ShapeImage
    {
        get => _shapeImage;
        private set => this.RaiseAndSetIfChanged(ref _shapeImage, value);
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
        
        _conveyorPhotoService = new ConveyorPhotoService();
        _conveyorPhotoService.StatusChanged += message => Manager.Success("Успех", message);
        _conveyorPhotoService.ErrorOccurred += message => Manager.Error("Ошибка", message);

        StickerParameters = new StickerParametersViewModel()
        {
            Manager = Manager
        };
        _ = StickerParameters.InitializeAsync();
        ValidationResult = new StickerValidationResultViewModel(_webSocketService);

        StartStreamCommand = ReactiveCommand.CreateFromTask(StartStreamAsync);
        StopStreamCommand = ReactiveCommand.CreateFromTask(StopStreamAsync);
        SaveEmptyConveyorPhotoCommand = ReactiveCommand.CreateFromTask(SaveEmptyConveyorPhotoAsync);
        
        SaveEmptyConveyorPhotoCommand.ThrownExceptions.Subscribe(ex => 
            Manager.Error("Ошибка сохранения фона", ex.Message));
    }

    private void _webSocketService_ConnectionClosed()
    {
        Status = StreamStatus.Disconnected;
    }

    private void _webSocketService_MessageReceived(StreamingMessage obj)
    {
        if(obj.Content is ImageStreamingMessageContent imageContent)
        {
            if (obj.Type == StreamingMessageType.RAW)
            {
                
                var bytes = imageContent.ToImageBytes();

                using var stream = new MemoryStream(bytes);

                RawImage = new(stream);
            }
            else if(obj.Type == StreamingMessageType.SHAPE)
            {
                var bytes = imageContent.ToImageBytes();

                using var stream = new MemoryStream(bytes);

                ShapeImage = new(stream);

            }
        }
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
    
    private async Task SaveEmptyConveyorPhotoAsync()
    {
        if (Status != StreamStatus.Running)
        {
            Manager.Error("Ошибка", "Трансляция не активна. Запустите трансляцию для сохранения фона.");
            return;
        }
        
        if (RawImage == null)
        {
            Manager.Error("Ошибка", "Нет доступного изображения для сохранения.");
            return;
        }
        
        string currentImageBase64;
        using (MemoryStream ms = new MemoryStream())
        {
            RawImage.Save(ms);
            byte[] imageBytes = ms.ToArray();
            currentImageBase64 = Convert.ToBase64String(imageBytes);
        }
        
        await _conveyorPhotoService.SaveEmptyConveyorPhotoAsync(currentImageBase64);
    }
}
