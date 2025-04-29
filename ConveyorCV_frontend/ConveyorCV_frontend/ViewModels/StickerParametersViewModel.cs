using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;
using System;
using System.IO;
using System.Linq;
using System.Reactive;
using System.Reactive.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels;

public class StickerParametersViewModel : ViewModelBase
{
    private readonly StickerParametersService _stickerParametersService;
    private string? _status;
    public string? Status
    {
        get => _status;
        set => this.RaiseAndSetIfChanged(ref _status, value);
    }
    private string? _imagePath = null;
    public string? ImagePath
    {
        get => _imagePath;
        set => this.RaiseAndSetIfChanged(ref _imagePath, value);
    }

    private Bitmap? _image;
    public Bitmap? Image
    {
        get => _image;
        set => this.RaiseAndSetIfChanged(ref _image, value);
    }

    private PointViewModel _center = new(300f, 200f);
    public PointViewModel Center
    {
        get => _center;
        set
        {
            this.RaiseAndSetIfChanged(ref _center, value);
            this.RaisePropertyChanged();
        }
    }
    

    private SizeViewModel _stickerSize = new(400f, 200f);
    public SizeViewModel StickerSize
    {
        get => _stickerSize;
        set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
    }

    private double _rotation = 0;
    public double Rotation
    {
        get => _rotation;
        set => this.RaiseAndSetIfChanged(ref _rotation, value);
    }

    private SizeViewModel _accSize = new(600f, 400f);
    public SizeViewModel AccSize
    {
        get => _accSize;
        set => this.RaiseAndSetIfChanged(ref _accSize, value);
    }

    public ReactiveCommand<Unit, Unit> SelectImageCommand { get; }
    public ReactiveCommand<Unit, Unit> ApplyParametersCommand { get; }
    public ReactiveCommand<Unit, Unit> FetchParametersCommand { get; }

    public StickerParametersViewModel()
    {
        _stickerParametersService = new StickerParametersService();
        _stickerParametersService.StatusChanged += message => Status = message;
        _stickerParametersService.ErrorOccurred += message => Status = message;
        SelectImageCommand = ReactiveCommand.CreateFromTask(SelectImage);
        var canApply = this.WhenAnyValue(x => x.Image).Select(image => image != null);
        ApplyParametersCommand = ReactiveCommand.CreateFromTask(ApplyParameters, canApply);
        FetchParametersCommand = ReactiveCommand.CreateFromTask(FetchParameters);

        StickerSize.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(SizeViewModel.Width))
            {
                UpdateHeight();
            }
            else if (e.PropertyName == nameof(SizeViewModel.Height))
            {
                UpdateWidth();
            }
        };
    }
    
    public async Task InitializeAsync()
    {
        await FetchParameters();
    }

    // fetches current parameters from backend. should be called on startup and on button click (button does not exist yet)
    private async Task FetchParameters()
    {
        try
        {
            var parameters = await _stickerParametersService.GetParametersAsync();
            if (parameters == null)
                return;

            AccSize = new SizeViewModel(parameters.AccSize.Width, parameters.AccSize.Height);
            StickerSize = new SizeViewModel(parameters.StickerSize.Width, parameters.StickerSize.Height);
            Center = new PointViewModel(parameters.StickerCenter.X, parameters.StickerCenter.Y);
            Rotation = parameters.StickerRotation;

            using (var stream = new MemoryStream(parameters.StickerDesign.ToDecodedBytes()))
            {
                Image = new Bitmap(stream);
                ImagePath = "Загружено с сервера";
            }
    
            UpdateHeight();

            Status = "Параметры наклейки загружены с сервера";
        }
        catch (Exception ex)
        {
            Status = $"Ошибка загрузки параметров: {ex.Message}";
        }
    }

    private async Task ApplyParameters()
    {
        using var stream = new MemoryStream();
        Image!.Save(stream);

        var parameters = new StickerValidationParametersDTO(
            stream.ToArray().ToEncodedString(),
            new((float)Center.X, (float)Center.Y),
            new((float)StickerSize.Width, (float)StickerSize.Height),
            Rotation,
            new((float)AccSize.Width, (float)AccSize.Height)
        );

        await _stickerParametersService.SetParametersAsync(parameters);
    }

    private async Task SelectImage()
    {
        var result = await DialogService.ShowOpenFileDialog("Выбор макета", Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));

        if (!string.IsNullOrWhiteSpace(result))
        {
            var filename = Path.GetFileName(result);
            ImagePath = result;
            Status = $"Выбран файл: {filename}";
            LoadImage(result);
        }
    }

    private void LoadImage(string path)
    {
        if (!string.IsNullOrEmpty(path))
        {
            try
            {
                using var fileStream = File.OpenRead(path);
                Image = new Bitmap(fileStream);
                UpdateHeight();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Exception: {ex.Message}");
            }
        }
    }

    private void UpdateHeight()
    {
        if (Image != null && StickerSize.Width > 0)
        {
            var aspectRatio = Image.Size.AspectRatio;
            var newHeight = StickerSize.Width / aspectRatio;
            StickerSize.Height = (float)newHeight;
        }

        Center?.RaisePropertyChanged(nameof(Center.Y));
    }

    private void UpdateWidth()
    {
        if (Image != null && StickerSize.Height > 0)
        {
            var aspectRatio = Image.Size.AspectRatio;
            var newWidth = StickerSize.Height * aspectRatio;
            StickerSize.Width = (float)newWidth;
        }

        Center?.RaisePropertyChanged(nameof(Center.X));
    }
}