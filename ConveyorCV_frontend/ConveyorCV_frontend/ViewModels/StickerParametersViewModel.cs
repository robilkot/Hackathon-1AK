using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;
using System;
using System.IO;
using System.Reactive;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels;

public class StickerParametersViewModel : ViewModelBase
{
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
        SelectImageCommand = ReactiveCommand.CreateFromTask(SelectImage);
        ApplyParametersCommand = ReactiveCommand.CreateFromTask(ApplyParameters);
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

    // fetches current parameters from backend. should be called on startup and on button click (button does not exist yet)
    private async Task FetchParameters()
    {
        // todo
    }

    // todo ensure that Image is not null (subscribe CanExecute of this command to validator or smth)
    private async Task ApplyParameters()
    {
        using var stream = new MemoryStream();
        Image.Save(stream);
        byte[] imageBytes = stream.ToArray();

        var parameters = new StickerValidationParametersDTO(
            imageBytes,
            new((float)Center.X, (float)Center.Y),
            new((float)AccSize.Width, (float)AccSize.Height),
            new((float)StickerSize.Width, (float)StickerSize.Height),
            Rotation
            );

        // todo send this to backend. ensure ok status code
    }

    private async Task SelectImage()
    {
        var result = await DialogService.ShowOpenFileDialog("Выбор макета", Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));

        if (!string.IsNullOrWhiteSpace(result))
        {
            var filename = Path.GetFileName(result);
            ImagePath = filename;
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