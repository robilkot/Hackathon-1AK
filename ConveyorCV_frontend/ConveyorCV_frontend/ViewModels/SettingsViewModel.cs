using Avalonia.Notification;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;
using System;
using System.Reactive;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels
{
    public class SettingsViewModel : ViewModelBase
    {
        public INotificationMessageManager Manager { get; } = new NotificationMessageManager();
        private readonly SettingsService _settingsService;

        // Camera settings
        private string _cameraType = "video";
        public string CameraType
        {
            get => _cameraType;
            set => this.RaiseAndSetIfChanged(ref _cameraType, value);
        }

        // Camera settings
        private string _phoneIp = "";
        public string PhoneIp
        {
            get => _phoneIp;
            set => this.RaiseAndSetIfChanged(ref _phoneIp, value);
        }

        private int _port = 8080;
        public int Port
        {
            get => _port;
            set => this.RaiseAndSetIfChanged(ref _port, value);
        }

        private string _videoPath = "";
        public string VideoPath
        {
            get => _videoPath;
            set => this.RaiseAndSetIfChanged(ref _videoPath, value);
        }

        // Processing settings
        private int _downscaleWidth = 1280;
        public int DownscaleWidth
        {
            get => _downscaleWidth;
            set => this.RaiseAndSetIfChanged(ref _downscaleWidth, value);
        }

        private int _downscaleHeight = 720;
        public int DownscaleHeight
        {
            get => _downscaleHeight;
            set => this.RaiseAndSetIfChanged(ref _downscaleHeight, value);
        }

        // Validation settings
        private float _positionTolerancePercent = 10.0f;
        public float PositionTolerancePercent
        {
            get => _positionTolerancePercent;
            set => this.RaiseAndSetIfChanged(ref _positionTolerancePercent, value);
        }

        private float _rotationToleranceDegrees = 5.0f;
        public float RotationToleranceDegrees
        {
            get => _rotationToleranceDegrees;
            set => this.RaiseAndSetIfChanged(ref _rotationToleranceDegrees, value);
        }

        private float _sizeRatioTolerance = 0.15f;
        public float SizeRatioTolerance
        {
            get => _sizeRatioTolerance;
            set => this.RaiseAndSetIfChanged(ref _sizeRatioTolerance, value);
        }

        // Detection settings
        private float _detectionBorderLeft = 0.32f;
        public float DetectionBorderLeft
        {
            get => _detectionBorderLeft;
            set => this.RaiseAndSetIfChanged(ref _detectionBorderLeft, value);
        }

        private float _detectionBorderRight = 0.68f;
        public float DetectionBorderRight
        {
            get => _detectionBorderRight;
            set => this.RaiseAndSetIfChanged(ref _detectionBorderRight, value);
        }

        private float _detectionLineHeight = 0.5f;
        public float DetectionLineHeight
        {
            get => _detectionLineHeight;
            set => this.RaiseAndSetIfChanged(ref _detectionLineHeight, value);
        }
        
        private string _settingsFilePath = "";
        public string SettingsFilePath
        {
            get => _settingsFilePath;
            set => this.RaiseAndSetIfChanged(ref _settingsFilePath, value);
        }

        // File paths
        private string _bgPhotoPath = "";
        public string BgPhotoPath
        {
            get => _bgPhotoPath;
            set => this.RaiseAndSetIfChanged(ref _bgPhotoPath, value);
        }

        private string _databaseUrl = "";
        public string DatabaseUrl
        {
            get => _databaseUrl;
            set => this.RaiseAndSetIfChanged(ref _databaseUrl, value);
        }

        private string _stickerParamsFile = "";
        public string StickerParamsFile
        {
            get => _stickerParamsFile;
            set => this.RaiseAndSetIfChanged(ref _stickerParamsFile, value);
        }

        private string _stickerDesignPath = "";
        public string StickerDesignPath
        {
            get => _stickerDesignPath;
            set => this.RaiseAndSetIfChanged(ref _stickerDesignPath, value);
        }

        private string _stickerOutputPath = "";
        public string StickerOutputPath
        {
            get => _stickerOutputPath;
            set => this.RaiseAndSetIfChanged(ref _stickerOutputPath, value);
        }

        // Commands
        public ReactiveCommand<Unit, Unit> LoadSettingsCommand { get; }
        public ReactiveCommand<Unit, Unit> SaveSettingsCommand { get; }
        public ReactiveCommand<Unit, Unit> SelectVideoPathCommand { get; }
        public ReactiveCommand<Unit, Unit> SelectBgPhotoPathCommand { get; }
        public ReactiveCommand<Unit, Unit> SelectSettingsFilePathCommand { get; }

        public SettingsViewModel()
        {
            _settingsService = new SettingsService();
            _settingsService.StatusChanged += message => Manager.Success(message);
            _settingsService.ErrorOccurred += message => Manager.Error("Ошибка настроек", message);

            LoadSettingsCommand = ReactiveCommand.CreateFromTask(LoadSettings);
            SaveSettingsCommand = ReactiveCommand.CreateFromTask(SaveSettings);
            SelectVideoPathCommand = ReactiveCommand.CreateFromTask(SelectVideoPath);
            SelectBgPhotoPathCommand = ReactiveCommand.CreateFromTask(SelectBgPhotoPath);
            SelectSettingsFilePathCommand = ReactiveCommand.CreateFromTask(SelectSettingsFilePath);
            
            // Load settings when view model is created
            _ = LoadSettings();
        }

        private async Task LoadSettings()
        {
            var settings = await _settingsService.GetSettingsAsync();
            if (settings != null)
            {
                CameraType = settings.CameraType ?? "video";
                BgPhotoPath = settings.BgPhotoPath ?? "";
                DatabaseUrl = settings.DatabaseUrl ?? "";
                StickerParamsFile = settings.StickerParamsFile ?? "";
                StickerDesignPath = settings.StickerDesignPath ?? "";
                StickerOutputPath = settings.StickerOutputPath ?? "";
                SettingsFilePath = settings.SettingsFilePath ?? "";
                
                if (settings.Camera != null)
                {
                    PhoneIp = settings.Camera.PhoneIp ?? "";
                    Port = settings.Camera.Port ?? 8080;
                    VideoPath = settings.Camera.VideoPath ?? "";
                }

                if (settings.Processing != null)
                {
                    DownscaleWidth = settings.Processing.DownscaleWidth ?? 1280;
                    DownscaleHeight = settings.Processing.DownscaleHeight ?? 720;
                }

                if (settings.Validation != null)
                {
                    PositionTolerancePercent = settings.Validation.PositionTolerancePercent ?? 10.0f;
                    RotationToleranceDegrees = settings.Validation.RotationToleranceDegrees ?? 5.0f;
                    SizeRatioTolerance = settings.Validation.SizeRatioTolerance ?? 0.15f;
                }

                if (settings.Detection != null)
                {
                    DetectionBorderLeft = settings.Detection.DetectionBorderLeft ?? 0.32f;
                    DetectionBorderRight = settings.Detection.DetectionBorderRight ?? 0.68f;
                    DetectionLineHeight = settings.Detection.DetectionLineHeight ?? 0.5f;
                }
            }
        }

        private async Task SaveSettings()
        {
            var settings = new SettingsDTO(
                CameraType,
                BgPhotoPath,
                DatabaseUrl,
                StickerParamsFile,
                StickerDesignPath,
                StickerOutputPath,
                SettingsFilePath,
                new ProcessingSettingsDTO(
                    DownscaleWidth,
                    DownscaleHeight
                ),
                new CameraSettingsDTO(
                    PhoneIp,
                    Port,
                    VideoPath
                ),
                new ValidationSettingsDTO(
                    PositionTolerancePercent,
                    RotationToleranceDegrees,
                    SizeRatioTolerance
                ),
                new DetectionSettingsDTO(
                    DetectionBorderLeft,
                    DetectionBorderRight,
                    DetectionLineHeight
                )
            );

            await _settingsService.ApplySettingsAsync(settings);
        }

        private async Task SelectVideoPath()
        {
            var result = await DialogService.ShowOpenFileDialog("Выбор видео", "");
            if (!string.IsNullOrEmpty(result))
            {
                VideoPath = result;
            }
        }

        private async Task SelectBgPhotoPath()
        {
            var result = await DialogService.ShowOpenFileDialog("Выбор фона", "");
            if (!string.IsNullOrEmpty(result))
            {
                BgPhotoPath = result;
            }
        }
        private async Task SelectSettingsFilePath()
        {
            var result = await DialogService.ShowOpenFileDialog("Выбор файла настроек", "");
            if (!string.IsNullOrEmpty(result))
            {
                SettingsFilePath = result;
            }
        }
    }
}