using System;
using Avalonia.Controls;
using Avalonia.Markup.Xaml;
using ConveyorCV_frontend.ViewModels;

namespace ConveyorCV_frontend.Views;

public partial class StickerValidationResultView : UserControl
{
    public StickerValidationResultView()
    {
        InitializeComponent();
        
        // Add data context change handling
        DataContextChanged += OnDataContextChanged;
    }
    
    private void OnDataContextChanged(object sender, EventArgs e)
    {
        // Update loading state when data context changes
        if (DataContext is StickerValidationResultViewModel viewModel)
        {
            // Subscribe to property changes if needed
            viewModel.PropertyChanged += (s, args) => {
                if (args.PropertyName == nameof(StickerValidationResultViewModel.Image))
                {
                    // Could update UI elements based on image loading state
                }
            };
        }
    }
}