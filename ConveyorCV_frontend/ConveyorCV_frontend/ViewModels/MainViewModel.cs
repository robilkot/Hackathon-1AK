using ConveyorCV_frontend.ViewModels;
using ReactiveUI;

public class MainViewModel : ViewModelBase
{
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

    private StreamViewModel _streamViewModel;
    public StreamViewModel StreamViewModel
    {
        get => _streamViewModel;
        set => this.RaiseAndSetIfChanged(ref _streamViewModel, value);
    }

    public MainViewModel()
    {
        StickerParameters = new StickerParametersViewModel();
        ValidationResult = new StickerValidationResultViewModel();
        StreamViewModel = new StreamViewModel(ValidationResult);
    }
}