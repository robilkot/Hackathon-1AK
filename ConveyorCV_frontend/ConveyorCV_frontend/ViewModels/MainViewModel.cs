using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels;

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

    public MainViewModel()
    {
        StickerParameters = new StickerParametersViewModel();
        ValidationResult = new StickerValidationResultViewModel();
    }
}
