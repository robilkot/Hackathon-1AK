using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Reactive;
using System.Threading.Tasks;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;

namespace ConveyorCV_frontend.ViewModels
{
    public class ValidationLogsViewModel : ViewModelBase
    {
        private readonly ValidationLogService _logService;

        private ObservableCollection<ValidationLogItemDTO> _logs;

        public ObservableCollection<ValidationLogItemDTO> Logs
        {
            get => _logs;
            private set => this.RaiseAndSetIfChanged(ref _logs, value);
        }


        private DateTimeOffset? _startDateTime;

        public DateTimeOffset? StartDateTime
        {
            get => _startDateTime;
            set
            {
                this.RaiseAndSetIfChanged(ref _startDateTime, value);
                if (value.HasValue && !_updatingStartText)
                {
                    _updatingStartText = true;
                    StartDateTimeText = value.Value.ToString("dd.MM.yyyy HH:mm");
                    _updatingStartText = false;
                }
            }
        }

        private DateTimeOffset? _endDateTime;

        public DateTimeOffset? EndDateTime
        {
            get => _endDateTime;
            set
            {
                this.RaiseAndSetIfChanged(ref _endDateTime, value);
                if (value.HasValue && !_updatingEndText)
                {
                    _updatingEndText = true;
                    EndDateTimeText = value.Value.ToString("dd.MM.yyyy HH:mm");
                    _updatingEndText = false;
                }
            }
        }

        private string _startDateTimeText = string.Empty;
        private bool _updatingStartText;

        public string StartDateTimeText
        {
            get => _startDateTimeText;
            set
            {
                this.RaiseAndSetIfChanged(ref _startDateTimeText, value);
                if (!_updatingStartText)
                {
                    _updatingStartText = true;
                    if (DateTimeOffset.TryParseExact(value, "dd.MM.yyyy HH:mm", null,
                            System.Globalization.DateTimeStyles.None, out var dt))
                    {
                        StartDateTime = dt;
                        StartDateTimeError = null;
                    }
                    else
                    {
                        StartDateTimeError = "Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ";
                    }

                    _updatingStartText = false;
                }
            }
        }

        private string _endDateTimeText = string.Empty;
        private bool _updatingEndText;

        public string EndDateTimeText
        {
            get => _endDateTimeText;
            set
            {
                this.RaiseAndSetIfChanged(ref _endDateTimeText, value);
                if (!_updatingEndText)
                {
                    _updatingEndText = true;
                    if (DateTimeOffset.TryParseExact(value, "dd.MM.yyyy HH:mm", null,
                            System.Globalization.DateTimeStyles.None, out var dt))
                    {
                        EndDateTime = dt;
                        EndDateTimeError = null;
                    }
                    else
                    {
                        EndDateTimeError = "Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ";
                    }

                    _updatingEndText = false;
                }
            }
        }

        private string _startDateTimeError;

        public string StartDateTimeError
        {
            get => _startDateTimeError;
            set => this.RaiseAndSetIfChanged(ref _startDateTimeError, value);
        }

        private string _endDateTimeError;

        public string EndDateTimeError
        {
            get => _endDateTimeError;
            set => this.RaiseAndSetIfChanged(ref _endDateTimeError, value);
        }

        private int _currentPage = 1;

        public int CurrentPage
        {
            get => _currentPage;
            set => this.RaiseAndSetIfChanged(ref _currentPage, value);
        }

        private int _pageSize = 10;

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
        
            Logs = new ObservableCollection<ValidationLogItemDTO>();
        
            LoadLogsCommand = ReactiveCommand.CreateFromTask(LoadLogs);
            NextPageCommand = ReactiveCommand.CreateFromTask(NextPage);
            PreviousPageCommand = ReactiveCommand.CreateFromTask(PreviousPage);
            FirstPageCommand = ReactiveCommand.CreateFromTask(FirstPage);
            LastPageCommand = ReactiveCommand.CreateFromTask(LastPage);
            DeleteLogCommand = ReactiveCommand.CreateFromTask<int>(DeleteLog);
        

            EndDateTime = DateTimeOffset.Now;
            StartDateTime = EndDateTime.Value.AddDays(-1);
        
            _ = LoadLogs();
        }

        private async Task LoadLogs()
        {
            var response = await _logService.GetLogsAsync(StartDateTime, EndDateTime, CurrentPage, PageSize);
        
            if (response != null)
            {
                Logs.Clear();
                foreach (var log in response.Logs)
                    Logs.Add(log);
            
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
                var logToRemove = Logs.FirstOrDefault(log => log.Id == logId);
                if (logToRemove != null)
                    Logs.Remove(logToRemove);
                
                TotalRecords--;
                TotalPages = (int)Math.Ceiling(TotalRecords / (double)PageSize);
        
                if (CurrentPage > TotalPages && TotalPages > 0)
                    await LoadLogs(); 
            }
        }
    }
}