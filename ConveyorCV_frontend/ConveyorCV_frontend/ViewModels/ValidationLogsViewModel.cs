using System;
using System.Collections.ObjectModel;
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
        
        private DateTimeOffset? _startDate;
        public DateTimeOffset? StartDate
        {
            get => _startDate;
            set => this.RaiseAndSetIfChanged(ref _startDate, value);
        }
        
        private DateTimeOffset? _endDate;
        public DateTimeOffset? EndDate
        {
            get => _endDate;
            set => this.RaiseAndSetIfChanged(ref _endDate, value);
        }
        
        private int _currentPage = 1;
        public int CurrentPage
        {
            get => _currentPage;
            set => this.RaiseAndSetIfChanged(ref _currentPage, value);
        }
        
        private int _pageSize = 20;
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
            
            // Initialize with default dates (last 7 days)
            EndDate = DateTimeOffset.Now;
            StartDate = EndDate.Value.AddDays(-7);
            
            // Load initial data
            _ = LoadLogs();
        }
        
        private async Task LoadLogs()
        {
            var response = await _logService.GetLogsAsync(StartDate, EndDate, CurrentPage, PageSize);
            
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
    }
}