using Avalonia.Controls;
using Avalonia.Notification;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ConveyorCV_frontend.Views;
using DynamicData;
using ReactiveUI;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Reactive;
using System.Reactive.Disposables;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels
{
    public class ValidationLogsViewModel : ViewModelBase, IDisposable
    {
        public INotificationMessageManager Manager { get; } = new NotificationMessageManager();
        
        private readonly ValidationLogService _logService;
        private readonly SourceCache<ValidationLogItemDTO, int> _logsCache;
        private readonly CompositeDisposable _disposables = new();

        private ReadOnlyObservableCollection<ValidationLogItemDTO> _logs;
        public ReadOnlyObservableCollection<ValidationLogItemDTO> Logs => _logs;


        private DateTime _startDate;
        public DateTime StartDate
        {
            get => _startDate;
            set => this.RaiseAndSetIfChanged(ref _startDate, value);
        }
        private TimeSpan _startTime;
        public TimeSpan StartTime
        {
            get => _startTime;
            set => this.RaiseAndSetIfChanged(ref _startTime, value);
        }

        private DateTime _endDate;
        public DateTime EndDate
        {
            get => _endDate;
            set => this.RaiseAndSetIfChanged(ref _endDate, value);
        }
        private TimeSpan _endTime;
        public TimeSpan EndTime
        {
            get => _endTime;
            set => this.RaiseAndSetIfChanged(ref _endTime, value);
        }



        private int _currentPage = 1;

        public int CurrentPage
        {
            get => _currentPage;
            set => this.RaiseAndSetIfChanged(ref _currentPage, value);
        }

        private int _pageSize = 15;

        public int PageSize
        {
            get => _pageSize;
            set => this.RaiseAndSetIfChanged(ref _pageSize, value);
        }

        private int _totalPages = 1;

        public int TotalPages
        {
            get => _totalPages;
            set => this.RaiseAndSetIfChanged(ref _totalPages, value);
        }

        private int _totalRecords = 0;

        public int TotalRecords
        {
            get => _totalRecords;
            set => this.RaiseAndSetIfChanged(ref _totalRecords, value);
        }

        private ValidationStatisticsDTO? _validationStats;

        public ValidationStatisticsDTO? ValidationStats
        {
            get => _validationStats;
            set => this.RaiseAndSetIfChanged(ref _validationStats, value);
        }

        public ReactiveCommand<Unit, Unit> LoadLogsCommand { get; }
        public ReactiveCommand<Unit, Unit> NextPageCommand { get; }
        public ReactiveCommand<Unit, Unit> PreviousPageCommand { get; }
        public ReactiveCommand<Unit, Unit> FirstPageCommand { get; }
        public ReactiveCommand<Unit, Unit> LastPageCommand { get; }
        public ReactiveCommand<int, Unit> DeleteLogCommand { get; }
        public ReactiveCommand<Unit, Unit> CloseStatisticsCommand { get; }
        public ReactiveCommand<Unit, Unit> LoadStatisticsCommand { get; }
        public ReactiveCommand<ValidationLogItemDTO, Unit> ViewResultCommand { get; }


        public ValidationLogsViewModel()
        {
            _logService = new ValidationLogService();
            _logService.StatusChanged += message => Manager.Success(message);
            _logService.ErrorOccurred += message => Manager.Error("Ошибка журнала", message);

            _logsCache = new SourceCache<ValidationLogItemDTO, int>(x => x.Id);
            _logsCache.Connect()
                .Bind(out _logs)
                .Subscribe()
                .DisposeWith(_disposables);

            LoadLogsCommand = ReactiveCommand.CreateFromTask(LoadLogs);
            NextPageCommand = ReactiveCommand.CreateFromTask(NextPage);
            PreviousPageCommand = ReactiveCommand.CreateFromTask(PreviousPage);
            FirstPageCommand = ReactiveCommand.CreateFromTask(FirstPage);
            LastPageCommand = ReactiveCommand.CreateFromTask(LastPage);
            DeleteLogCommand = ReactiveCommand.CreateFromTask<int>(DeleteLog);
            CloseStatisticsCommand = ReactiveCommand.Create(CloseStatistics);
            LoadStatisticsCommand = ReactiveCommand.CreateFromTask(LoadStatistics);
            ViewResultCommand = ReactiveCommand.CreateFromTask<ValidationLogItemDTO>(ViewResult);

            StartDate = DateTime.Now - TimeSpan.FromHours(12);
            StartTime = StartDate.TimeOfDay;

            EndDate = DateTime.Now;
            EndTime = EndDate.TimeOfDay + TimeSpan.FromHours(12);

            _ = LoadLogs();
        }

        private void CloseStatistics()
        {
            ValidationStats = null;
        }

        private async Task LoadStatistics()
        {
            DateTimeOffset start = StartDate - StartDate.TimeOfDay + StartTime;
            DateTimeOffset end = EndDate - EndDate.TimeOfDay + EndTime;

            var response = await _logService.GetStatisticsAsync(start, end);

            if (response != null)
            {
                ValidationStats = response;
            }
        }

        private async Task LoadLogs()
        {
            DateTimeOffset start = StartDate - StartDate.TimeOfDay + StartTime;
            DateTimeOffset end = EndDate - EndDate.TimeOfDay + EndTime;

            var response = await _logService.GetLogsAsync(start, end, CurrentPage, PageSize);

            if (response != null)
            {
                _logsCache.Edit(innerCache => innerCache.Clear());
                var sortedLogs = response.Logs.OrderByDescending(log => log.Timestamp).ToList();
                _logsCache.Edit(innerCache => innerCache.AddOrUpdate(sortedLogs));
        
                TotalPages = response.Pages;
                TotalRecords = response.Total;
            }
        }

        private async Task NextPage()
        {
            if (CurrentPage < TotalPages)
            {
                CurrentPage++;
                await LoadLogs();
            }
        }

        private async Task PreviousPage()
        {
            if (CurrentPage > 1)
            {
                CurrentPage--;
                await LoadLogs();
            }
        }

        private async Task FirstPage()
        {
            CurrentPage = 1;
            await LoadLogs();
        }

        private async Task LastPage()
        {
            CurrentPage = TotalPages;
            await LoadLogs();
        }

        private async Task DeleteLog(int logId)
        {
            var success = await _logService.DeleteLogAsync(logId);
            if (success)
            {
                _logsCache.Remove(logId);

                TotalRecords--;
                TotalPages = (int)Math.Ceiling(TotalRecords / (double)PageSize);

                if (CurrentPage > TotalPages && TotalPages > 0)
                    await LoadLogs();
            }
        }

        private async Task ViewResult(ValidationLogItemDTO log)
        {
            var vm = new StickerValidationResultViewModel();
            var defaultImg = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
            vm.LastResult = new(log.Image ?? defaultImg, 
                log.Timestamp, 
                log.SeqNumber, 
                log.StickerPresent, 
                log.StickerMatchesDesign, 
                log.StickerSize, 
                log.StickerPosition, 
                log.StickerRotation);

            var _validationLogsWindow = new StickerValidationResultWindow
            {
                DataContext = vm
            };
            _validationLogsWindow.Show();
            _validationLogsWindow.Activate();
        }

        public void Dispose()
        {
            _disposables.Dispose();
        }
    }
}