using System;
using System.Collections.Generic;
using System.Globalization;
using Avalonia.Data;
using Avalonia.Data.Converters;
using ConveyorCV_frontend.ViewModels;

namespace ConveyorCV_frontend.Converters;

public class StickerParametersToXConverter : IMultiValueConverter
{

    public object? Convert(IList<object?> values, Type targetType, object? parameter, CultureInfo culture)
    {
        if (values[0] is double x && values[1] is SizeViewModel vm)
            return x - vm.Width / 2;

        return 0;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}