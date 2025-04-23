using System;
using System.Globalization;
using Avalonia.Data.Converters;

namespace ConveyorCV_frontend.Converters;

public class HalfSizeConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double size)
            return size * 0.40;
        return double.NaN;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}