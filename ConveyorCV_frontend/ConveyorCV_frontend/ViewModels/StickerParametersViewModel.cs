using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;
using System;
using System.Drawing;
using System.IO;
using System.Reactive;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels;

public class StickerParametersViewModel : ViewModelBase
{
    private readonly StickerParametersService _stickerService;
    private string _imagePath;
    private Bitmap? _image;
    private PointViewModel? _center = new(300f, 200f);
    private SizeViewModel _stickerSize = new(400f, 200f);
    private double _rotation = 0;
    private SizeViewModel _accSize = new(600f, 400f);
    private string _status;

    public string ImagePath
    {
        get => _imagePath;
        set => this.RaiseAndSetIfChanged(ref _imagePath, value);
    }

    public Bitmap? Image
    {
        get => _image;
        set => this.RaiseAndSetIfChanged(ref _image, value);
    }

    public PointViewModel? Center
    {
        get => _center;
        set
        {
            this.RaiseAndSetIfChanged(ref _center, value);
            this.RaisePropertyChanged();
        }
    }

    public SizeViewModel StickerSize
    {
        get => _stickerSize;
        set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
    }

    public double Rotation
    {
        get => _rotation;
        set => this.RaiseAndSetIfChanged(ref _rotation, value);
    }

    public SizeViewModel AccSize
    {
        get => _accSize;
        set => this.RaiseAndSetIfChanged(ref _accSize, value);
    }

    public string Status
    {
        get => _status;
        set => this.RaiseAndSetIfChanged(ref _status, value);
    }

    public ReactiveCommand<Unit, Unit> SelectImageCommand { get; }
    public ReactiveCommand<Unit, Unit> ApplyCommand { get; }

    public StickerParametersViewModel()
    {
        _stickerService = new StickerParametersService();
        
        _stickerService.StatusChanged += msg => Status = msg;
        _stickerService.ErrorOccurred += msg => Status = msg;
        
        SelectImageCommand = ReactiveCommand.CreateFromTask(SelectImage);
        ApplyCommand = ReactiveCommand.CreateFromTask(ApplyParameters);
        
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

    private async Task ApplyParameters()
    {
        if (string.IsNullOrEmpty(ImagePath) || Image == null)
        {
            Status = "Ошибка: Не выбрано изображение макета";
            return;
        }

        try
        {
            Status = "Подготовка параметров...";
            
            // Convert image to base64
            string base64Image = ConvertImageToBase64(ImagePath);
            if (string.IsNullOrEmpty(base64Image))
            {
                Status = "Ошибка: Не удалось конвертировать изображение";
                return;
            }
            
            var parametersDto = StickerParametersDTO.FromViewModel(this, base64Image);
            
            await _stickerService.SetParametersAsync(parametersDto);
        }
        catch (Exception ex)
        {
            Status = $"Ошибка: {ex.Message}";
        }
    }

    private string ConvertImageToBase64(string imagePath)
    {
        return StickerParametersService.ImageToBase64(imagePath);
    }

    private async Task SelectImage()
    {
        var result = await DialogService.ShowOpenFileDialog("Выбор макета", 
            Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));

        if (!string.IsNullOrWhiteSpace(result))
        {
            var filename = Path.GetFileName(result);
            ImagePath = result; // Store full path for later use
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
                Status = "Изображение загружено";
            }
            catch (Exception ex)
            {
                Status = $"Ошибка загрузки: {ex.Message}";
            }
        }
    }

    private void UpdateHeight()
    {
        if (Image != null && StickerSize.Width > 0)
        {
            var aspectRatio = Image.Size.AspectRatio;
            var newHeight = StickerSize.Width / aspectRatio;
            StickerSize.Height = newHeight;
        }

        Center?.RaisePropertyChanged(nameof(Center.Y));
    }

    private void UpdateWidth()
    {
        if (Image != null && StickerSize.Height > 0)
        {
            var aspectRatio = Image.Size.AspectRatio;
            var newWidth = StickerSize.Height * aspectRatio;
            StickerSize.Width = newWidth;
        }

        Center?.RaisePropertyChanged(nameof(Center.X));
    }
}