using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using DynamicData;
using ReactiveUI;
using System;
using System.Collections.ObjectModel;
using System.Reactive;
using System.Reactive.Disposables;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.ViewModels
{
    public class ValidationLogsViewModel : ViewModelBase, IDisposable
    {
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

        private string _status = "Готово";

        public string Status
        {
            get => _status;
            set => this.RaiseAndSetIfChanged(ref _status, value);
        }

        public ReactiveCommand<Unit, Unit> LoadLogsCommand { get; }
        public ReactiveCommand<Unit, Unit> NextPageCommand { get; }
        public ReactiveCommand<Unit, Unit> PreviousPageCommand { get; }
        public ReactiveCommand<Unit, Unit> FirstPageCommand { get; }
        public ReactiveCommand<Unit, Unit> LastPageCommand { get; }
        public ReactiveCommand<int, Unit> DeleteLogCommand { get; }

        public ValidationLogsViewModel()
        {
            _logService = new ValidationLogService();
            _logService.StatusChanged += message => Status = message;
            _logService.ErrorOccurred += message => Status = message;

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

            StartDate = DateTime.Now - TimeSpan.FromDays(1);
            StartTime = StartDate.TimeOfDay;

            EndDate = DateTime.Now;
            EndTime = EndDate.TimeOfDay + TimeSpan.FromHours(1);

            _ = LoadLogs();
        }

        private async Task LoadLogs()
        {
            DateTimeOffset start = StartDate - StartDate.TimeOfDay + StartTime;
            DateTimeOffset end = EndDate - StartDate.TimeOfDay + EndTime;

            var response = await _logService.GetLogsAsync(start, end, CurrentPage, PageSize);

            if (response != null)
            {
                _logsCache.Edit(innerCache =>
                {
                    innerCache.Clear();
                    innerCache.AddOrUpdate(response.Logs);
                });

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
        public void Dispose()
        {
            _disposables.Dispose();
        }
    }
}