using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.Services
{
    public static class DialogService
    {
        // todo smells shit
        public async static Task<string> ShowOpenFileDialog(string title, string directory)
        {
            var path = string.Empty;
            if (App.Current.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop
                && desktop.MainWindow is not null)
            {
                var extensions = new List<string>() { "jpg", "png", "bmp" };
                var filters = new List<FileDialogFilter>() {
                    new FileDialogFilter { Name = "Images", Extensions = extensions }
                };
                var dialog = new OpenFileDialog
                {
                    Title = title,
                    Directory = directory,
                    Filters = filters,
                    AllowMultiple = false,
                };

                var results = await dialog.ShowAsync(desktop.MainWindow);
                path = results.FirstOrDefault() ?? path;
            }
            return path;
        }

        public async static Task<string> ShowSaveFileDialog(string title, string directory, string name)
        {
            var path = string.Empty;
            if (Application.Current.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop
                && desktop.MainWindow is not null)
            {
                var filter = new FileDialogFilter() { Name = "Images", Extensions = new List<string> { "png", "jpg", "bmp" } };
                var dialog = new SaveFileDialog
                {
                    Title = title,
                    Directory = directory,
                    InitialFileName = name,
                    Filters = new List<FileDialogFilter> { filter },
                };

                var result = await dialog.ShowAsync(desktop.MainWindow);
                path = result ?? path;
            }
            return path;
        }
    }
}
