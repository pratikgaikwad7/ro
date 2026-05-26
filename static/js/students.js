const API_URL = '/api/students';
const FILTER_URL = '/api/students/filters';
const BASE_YEAR = 2024; 

let studentsCache = [];
const modal = document.getElementById('studentModal');
const form = document.getElementById('studentForm');
const tableBody = document.getElementById('studentTableBody');
const emptyState = document.getElementById('emptyState');
const modalTitle = document.getElementById('modalTitle');

// --- BATCH LOGIC ---

function formatAcademicYear(year) {
    if (!year) return "";
    const nextYear = (year + 1).toString().slice(-2);
    return `${year}-${nextYear}`;
}

function getBatchFromYear(year) {
    if (!year) return "";
    return (parseInt(year) - BASE_YEAR) + 1;
}

function getYearFromBatch(batchNo) {
    if (!batchNo) return "";
    return BASE_YEAR + (parseInt(batchNo) - 1);
}

function populateBatchDropdowns() {
    const yearSelect = document.getElementById('batch_year');
    const batchSelect = document.getElementById('batch_no');
    
    yearSelect.innerHTML = '<option value="">Select Year</option>';
    batchSelect.innerHTML = '<option value="">Select Batch</option>';

    const currentYear = new Date().getFullYear();
    const futureLimit = currentYear + 5; 

    for (let y = BASE_YEAR; y <= futureLimit; y++) {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = formatAcademicYear(y);
        yearSelect.appendChild(opt);
    }

    const batchesNeeded = (futureLimit - BASE_YEAR) + 1;
    for (let b = 1; b <= batchesNeeded; b++) {
        const opt = document.createElement('option');
        opt.value = b;
        opt.textContent = `Batch ${b}`;
        batchSelect.appendChild(opt);
    }
}

function syncBatchFromYear(context) {
    const yearSelect = (context === 'modal') 
        ? document.getElementById('batch_year') 
        : document.getElementById('filter_year');
    const batchSelect = (context === 'modal') 
        ? document.getElementById('batch_no') 
        : document.getElementById('filter_batch_no');

    const selectedYear = yearSelect.value;
    if (selectedYear) {
        batchSelect.value = getBatchFromYear(selectedYear);
    }
}

function syncYearFromBatch(context) {
    const yearSelect = (context === 'modal') 
        ? document.getElementById('batch_year') 
        : document.getElementById('filter_year');
    const batchSelect = (context === 'modal') 
        ? document.getElementById('batch_no') 
        : document.getElementById('filter_batch_no');

    const selectedBatch = batchSelect.value;
    if (selectedBatch) {
        yearSelect.value = getYearFromBatch(selectedBatch);
    }
}

// --- END DATE LOGIC ---

function updateEndDate() {
    const dojInput = document.getElementById('date_of_joining').value;
    const endDisplay = document.getElementById('end_date_display');
    
    if (dojInput) {
        const parts = dojInput.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]) - 1; 
        const day = parseInt(parts[2]);

        let endYear = year + 5;
        let endDay = day;
        let endMonth = month;

        // Handle Leap Year case for Feb 29
        if (month === 1 && day === 29) { 
            const isLeap = new Date(endYear, 1, 29).getMonth() === 1;
            if (!isLeap) endDay = 28;
        }

        const finalDate = new Date(endYear, endMonth, endDay);
        const formattedDate = finalDate.toISOString().split('T')[0];
        endDisplay.value = formattedDate;
    } else {
        endDisplay.value = '';
    }
}

// --- CORE APP ---

document.addEventListener('DOMContentLoaded', async () => {
    populateBatchDropdowns(); 
    await loadFilterOptions(); 
    setCurrentYearFilter();   
    loadStudents();            
});

async function loadFilterOptions() {
    try {
        const response = await fetch(FILTER_URL);
        const data = await response.json();

        const locationSelect = document.getElementById('filter_location');
        locationSelect.innerHTML = '<option value="">All Locations</option>';
        data.locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc; 
            option.textContent = loc.replace(/_/g, ' '); 
            locationSelect.appendChild(option);
        });

        populateSelect('filter_department', data.departments);
        populateSelect('filter_bits_stream', data.bits_streams); // NEW
        populateSelect('filter_function', data.functions);
        populateSelectWithFormatter('filter_year', data.years, formatAcademicYear);
        populateSelectWithFormatter('filter_batch_no', data.batch_nos, b => `Batch ${b}`);

    } catch (err) { console.error('Failed to load filter options', err); }
}

function populateSelect(id, options) {
    const select = document.getElementById(id);
    const firstOption = select.options[0];
    select.innerHTML = '';
    select.appendChild(firstOption);
    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });
}

function populateSelectWithFormatter(id, options, formatter) {
    const select = document.getElementById(id);
    const firstOption = select.options[0];
    select.innerHTML = '';
    select.appendChild(firstOption);

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = formatter(opt);
        select.appendChild(option);
    });
}

function setCurrentYearFilter() {
    const currentYear = new Date().getFullYear();
    const yearSelect = document.getElementById('filter_year');
    const yearExists = Array.from(yearSelect.options).some(opt => opt.value == currentYear);
    if (yearExists) yearSelect.value = currentYear;
}

function getFilterParams() {
    const params = new URLSearchParams();
    const fields = ['location', 'year', 'department', 'batch_no', 'function', 'bits_stream', 'status']; // NEW bits_stream
    fields.forEach(f => {
        const val = document.getElementById(`filter_${f}`).value;
        if (val) params.append(f, val);
    });
    return params.toString();
}

async function loadStudents() {
    try {
        const queryString = getFilterParams();
        const response = await fetch(`${API_URL}?${queryString}`);
        const data = await response.json();
        studentsCache = data;
        renderTable(data);
    } catch (err) { console.error('Failed to load students', err); }
}

function renderTable(data) {
    tableBody.innerHTML = '';
    if (data.length === 0) { emptyState.classList.remove('hidden'); return; }
    emptyState.classList.add('hidden');

    data.forEach(student => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-slate-50 transition-colors group';
        const displayYear = student.batch_year ? formatAcademicYear(student.batch_year) : '-';
        const displayLocation = student.plant_location ? student.plant_location.replace(/_/g, ' ') : '-';
        
        const status = student.status || 'active';
        let badgeClass = 'bg-green-100 text-green-800';
        if(status === 'dropped') badgeClass = 'bg-red-100 text-red-800';
        if(status === 'completed') badgeClass = 'bg-blue-100 text-blue-800';
        const statusBadge = `<span class="px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${badgeClass} capitalize">${status}</span>`;

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-inner">
                        ${student.employee_name ? student.employee_name[0].toUpperCase() : 'N'}
                    </div>
                    <div class="ml-4">
                        <div class="text-sm font-semibold text-slate-900">${student.employee_name}</div>
                        <div class="text-xs text-slate-500">${student.ticket_no}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">${statusBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-slate-800">${displayLocation}</div>
                <div class="text-xs text-slate-500">${displayYear} | Batch: ${student.batch_no || '-'}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 font-medium">${student.department || '-'}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-slate-800">${student.mobile_no}</div>
                <div class="text-xs text-slate-400">${student.email || ''}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                 <button onclick="editStudent(${student.id})" class="text-indigo-600 hover:text-white hover:bg-indigo-600 border border-indigo-200 hover:border-indigo-600 px-3 py-1.5 rounded-md transition text-xs font-bold mr-2">
                    <i class="fas fa-edit mr-1"></i> Edit
                </button>
                <button onclick="deleteStudent(${student.id})" class="text-red-600 hover:text-white hover:bg-red-600 border border-red-200 hover:border-red-600 px-3 py-1.5 rounded-md transition text-xs font-bold">
                    <i class="fas fa-trash mr-1"></i> Delete
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function applyFilters() { loadStudents(); }

function clearFilters() {
    document.getElementById('filter_location').value = '';
    document.getElementById('filter_department').value = '';
    document.getElementById('filter_bits_stream').value = ''; // NEW
    document.getElementById('filter_batch_no').value = '';
    document.getElementById('filter_function').value = '';
    document.getElementById('filter_status').value = '';
    setCurrentYearFilter();
    loadStudents();
}

function openModal() {
    form.reset();
    document.getElementById('studentId').value = '';
    modalTitle.innerText = 'Add New Student';
    
    document.getElementById('batch_year').value = '';
    document.getElementById('batch_no').value = '';
    document.getElementById('end_date_display').value = '';
    document.getElementById('status').value = 'active';
    
    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closeModal() { 
    modal.classList.add('hidden'); 
    document.body.classList.remove('overflow-hidden');
}

async function editStudent(id) {
    const student = studentsCache.find(s => s.id === id);
    if (!student) return;
    
    const nameParts = (student.employee_name || "").trim().split(/\s+/);
    
    const firstName = nameParts[0] || '';
    const surname = nameParts.length > 1 ? nameParts[nameParts.length - 1] : '';
    const middleName = nameParts.length > 2 ? nameParts.slice(1, -1).join(' ') : '';

    document.getElementById('studentId').value = student.id;
    document.getElementById('first_name').value = firstName;
    document.getElementById('middle_name').value = middleName;
    document.getElementById('surname').value = surname;

    document.getElementById('ticket_no').value = student.ticket_no || '';
    document.getElementById('email').value = student.email || '';
    document.getElementById('gender').value = student.gender || '';
    document.getElementById('mobile_no').value = student.mobile_no || '';
    document.getElementById('diploma_branch').value = student.diploma_branch || '';
    document.getElementById('bits_stream').value = student.bits_stream || ''; // NEW
    document.getElementById('department').value = student.department || '';
    document.getElementById('reporting_manager').value = student.reporting_manager || '';
    document.getElementById('function').value = student.function || '';
    
    const dojValue = student.date_of_joining || '';
    document.getElementById('date_of_joining').value = dojValue;
    
    updateEndDate();
    
    document.getElementById('plant_location').value = student.plant_location || '';
    document.getElementById('batch_year').value = student.batch_year || '';
    document.getElementById('batch_no').value = student.batch_no || '';
    document.getElementById('status').value = student.status || 'active';

    modalTitle.innerText = 'Edit Student Details';
    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

async function deleteStudent(id) {
    if (!confirm('Are you sure you want to delete this student?')) return;
    try {
        const response = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
        if (response.ok) loadStudents(); else alert('Failed to delete');
    } catch (err) { console.error(err); }
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('studentId').value;
    const isEdit = !!id;
    
    const yearVal = document.getElementById('batch_year').value;
    const batchVal = document.getElementById('batch_no').value;

    const payload = {
        first_name: document.getElementById('first_name').value,
        middle_name: document.getElementById('middle_name').value,
        surname: document.getElementById('surname').value,
        
        ticket_no: document.getElementById('ticket_no').value,
        email: document.getElementById('email').value,
        gender: document.getElementById('gender').value,
        mobile_no: document.getElementById('mobile_no').value,
        diploma_branch: document.getElementById('diploma_branch').value,
        bits_stream: document.getElementById('bits_stream').value, // NEW
        department: document.getElementById('department').value,
        reporting_manager: document.getElementById('reporting_manager').value,
        function: document.getElementById('function').value,
        date_of_joining: document.getElementById('date_of_joining').value,
        plant_location: document.getElementById('plant_location').value,
        batch_year: yearVal ? parseInt(yearVal) : null,
        batch_no: batchVal ? parseInt(batchVal) : null,
        bc_no: '',
        status: document.getElementById('status').value
    };

    try {
        const url = isEdit ? `${API_URL}/${id}` : API_URL;
        const method = isEdit ? 'PUT' : 'POST';
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) { 
            closeModal(); 
            await loadStudents();
        } else { 
            const err = await response.json(); 
            alert('Error: ' + (err.error || 'Unknown error')); 
        }
    } catch (err) { console.error(err); alert('Failed to save student'); }
});

// --- EXCEL UPLOAD LOGIC ---

const uploadInput = document.getElementById('excelUploadInput');

uploadInput.addEventListener('change', function() {
    if (this.files && this.files[0]) {
        uploadExcelFile(this.files[0]);
    }
});

async function uploadExcelFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const uploadBtn = document.querySelector('button[onclick*="excelUploadInput"]');
    const originalText = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Uploading...';
    uploadBtn.disabled = true;

    try {
        const response = await fetch('/api/students/upload-excel', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showUploadResult(result);
            if (result.inserted > 0) {
                loadStudents();
            }
        } else {
            alert('Error uploading file: ' + (result.error || 'Unknown error'));
        }
    } catch (err) {
        console.error(err);
        alert('Failed to connect to server.');
    } finally {
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
        uploadInput.value = '';
    }
}

function showUploadResult(data) {
    document.getElementById('res-total').innerText = data.total_rows;
    document.getElementById('res-inserted').innerText = data.inserted;
    document.getElementById('res-skipped').innerText = data.skipped;
    document.getElementById('res-failed').innerText = data.failed;

    const errorContainer = document.getElementById('errorDetailsContainer');
    const errorList = document.getElementById('errorList');
    errorList.innerHTML = '';

    if (data.failed > 0 && data.errors && data.errors.length > 0) {
        errorContainer.classList.remove('hidden');
        data.errors.forEach(err => {
            const div = document.createElement('div');
            div.textContent = err;
            div.className = 'mb-1 border-b border-red-100 pb-1 last:border-0';
            errorList.appendChild(div);
        });
    } else {
        errorContainer.classList.add('hidden');
    }

    document.getElementById('uploadResultModal').classList.remove('hidden');
}

function closeUploadResult() {
    document.getElementById('uploadResultModal').classList.add('hidden');
}