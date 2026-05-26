// static/js/user_dashboard.js

Chart.register(ChartDataLabels);

const sidebar = document.getElementById('filterSidebar');
const studentTableContainer = document.getElementById('studentTableContainer');
const toggleTableText = document.getElementById('toggleTableText');
const toggleTableIcon = document.getElementById('toggleTableIcon');

let performanceChartInstance = null;
let genderChartInstance = null;

document.addEventListener('DOMContentLoaded', function() {
    if (window.dashboardConfig) {
        initGenderChart(window.dashboardConfig.maleCount, window.dashboardConfig.femaleCount);
        if (window.dashboardConfig.performanceData) {
            initPerformanceChart(window.dashboardConfig.performanceData);
        }
    }
    
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updatePerformanceChart);
    });
    
    document.addEventListener('click', function(event) {
        const isClickInsideDropdown = event.target.closest('.dropdown-menu');
        const isClickOnDropdownBtn = event.target.closest('.dropdown-btn');
        const isClickOnClearBtn = event.target.closest('button[onclick*="clearCheckboxes"]');

        if (!isClickInsideDropdown && !isClickOnDropdownBtn && !isClickOnClearBtn) {
            document.querySelectorAll('.dropdown-menu').forEach(dd => {
                dd.classList.add('hidden');
            });
        }
    });
});

function toggleSidebar() {
    sidebar.classList.toggle('open');
}

function toggleStudentTable() {
    const isHidden = studentTableContainer.classList.contains('hidden');
    if (isHidden) {
        studentTableContainer.classList.remove('hidden');
        toggleTableText.textContent = 'Hide Student Records';
        toggleTableIcon.classList.remove('fa-chevron-down');
        toggleTableIcon.classList.add('fa-chevron-up');
    } else {
        studentTableContainer.classList.add('hidden');
        toggleTableText.textContent = 'Show Student Records';
        toggleTableIcon.classList.remove('fa-chevron-up');
        toggleTableIcon.classList.add('fa-chevron-down');
    }
}

function toggleDropdown(id) {
    document.querySelectorAll('.dropdown-menu').forEach(dd => {
        if(dd.id !== id) dd.classList.add('hidden');
    });
    const menu = document.getElementById(id);
    if (menu) menu.classList.toggle('hidden');
}

function clearCheckboxes(type) {
    let selector = '';
    if(type === 'batch') selector = '.batch-checkbox';
    if(type === 'plant') selector = '.plant-checkbox';
    if(type === 'sem') selector = '.sem-checkbox';
    // Removed 'stream'
    
    document.querySelectorAll(selector).forEach(cb => cb.checked = false);
    updatePerformanceChart();
}

function openStudentModal(student) {
    document.getElementById('modal-title').textContent = student.employee_name || 'N/A';
    document.getElementById('modalAvatar').textContent = (student.employee_name || '?')[0].toUpperCase();
    document.getElementById('modalSub').innerHTML = `
        <span>${student.department || 'Unknown Dept'}</span> 
        <span class="w-1 h-1 rounded-full bg-slate-500"></span> 
        <span>${student.ticket_no || 'N/A'}</span>
    `;
    
    // Personal Info
    document.getElementById('mTicket').textContent = student.ticket_no || 'N/A';
    document.getElementById('mEmail').textContent = student.email || 'N/A';
    document.getElementById('mMobile').textContent = student.mobile_no || 'N/A';
    document.getElementById('mGender').textContent = student.gender || 'N/A';
    document.getElementById('mBC').textContent = student.bc_no || 'N/A';
    document.getElementById('mBranch').textContent = student.diploma_branch || 'N/A';
    
    // Professional Info
    const location = student.plant_location ? student.plant_location.replace(/_/g, ' ') : 'N/A';
    document.getElementById('mLocation').textContent = location;
    document.getElementById('mDept').textContent = student.department || 'N/A';
    document.getElementById('mFunction').textContent = student.function || 'N/A';
    document.getElementById('mManager').textContent = student.reporting_manager || 'N/A';
    document.getElementById('mStream').textContent = student.bits_stream || 'N/A';
    
    document.getElementById('mYear').textContent = formatAcademicYear(student.batch_year);
    document.getElementById('mBatch').textContent = student.batch_no ? `Batch ${student.batch_no}` : 'N/A';
    
    // Format Date of Joining
    if (student.date_of_joining) {
        const dateObj = new Date(student.date_of_joining);
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        document.getElementById('mDOJ').textContent = dateObj.toLocaleDateString('en-US', options);
    } else {
        document.getElementById('mDOJ').textContent = 'N/A';
    }

    const semHeader = document.getElementById('mSemHeader');
    const statusBadge = document.getElementById('mStatusBadge');
    const activeStatusSpan = document.getElementById('mActiveStatus');
    
    semHeader.textContent = `Semester ${student.semester || '-'}`;
    
    let badgeHtml = '';
    if(student.semester_status === 'completed') {
        badgeHtml = '<span class="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 border border-green-200 flex items-center gap-1"><i class="fas fa-check-circle"></i> Completed</span>';
    } else if (student.semester_status === 'ongoing') {
        badgeHtml = '<span class="px-3 py-1 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700 border border-yellow-200 flex items-center gap-1"><i class="fas fa-spinner fa-spin"></i> Ongoing</span>';
    } else {
        badgeHtml = '<span class="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">No Status</span>';
    }
    statusBadge.innerHTML = badgeHtml;
    
    activeStatusSpan.textContent = (student.student_status || 'N/A').capitalize();

    document.getElementById('studentModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closeStudentModal() {
    document.getElementById('studentModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}

function formatAcademicYear(year) {
    if (!year) return 'N/A';
    const nextYear = (parseInt(year) + 1).toString().slice(-2);
    return `${year}-${nextYear}`;
}

// Capitalize helper
String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
};

const centerTextPlugin = {
    id: 'centerText',
    beforeDraw(chart) {
        const { width, height, ctx } = chart;
        ctx.save();
        const total = chart.config.data.datasets[0].data.reduce((a, b) => a + b, 0);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 22px sans-serif';
        ctx.fillStyle = '#111827';
        ctx.fillText(total, width / 2, height / 2 - 8);
        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#6b7280';
        ctx.fillText('Total', width / 2, height / 2 + 14);
        ctx.restore();
    }
};

function initGenderChart(maleCount, femaleCount) {
    const ctx = document.getElementById('genderChart').getContext('2d');
    const total = maleCount + femaleCount;

    genderChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Male', 'Female'],
            datasets: [{
                data: [maleCount, femaleCount],
                backgroundColor: ['rgba(59, 130, 246, 0.9)', 'rgba(236, 72, 153, 0.9)'],
                borderColor: ['rgba(255, 255, 255, 1)', 'rgba(255, 255, 255, 1)'],
                borderWidth: 3,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: { display: true, position: 'bottom', labels: { color: '#374151', font: { size: 12, weight: 'bold' }, padding: 15, usePointStyle: true, pointStyle: 'circle' } },
                tooltip: { callbacks: { label: function(context) { let label = context.label || ''; if (label) label += ': '; if (context.parsed !== null) { const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0; label += `${context.parsed} (${percentage}%)`; } return label; } } },
                datalabels: { color: '#fff', anchor: 'center', align: 'center', font: { weight: 'bold', size: 14 }, formatter: (value) => value > 0 ? value : '' }
            }
        },
        plugins: [centerTextPlugin]
    });
}

function initPerformanceChart(data) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    const labels = data.map(item => item.range);
    const counts = data.map(item => item.count);

    if (performanceChartInstance) performanceChartInstance.destroy();

    const barColors = [
        'rgba(239, 68, 68, 0.85)',
        'rgba(249, 115, 22, 0.85)',
        'rgba(234, 179, 8, 0.85)',
        'rgba(132, 204, 22, 0.85)',
        'rgba(34, 197, 94, 0.85)',
        'rgba(6, 182, 212, 0.85)'
    ];

    performanceChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Students',
                data: counts,
                backgroundColor: barColors,
                borderRadius: 8,
                borderSkipped: false,
                barPercentage: 0.58,
                categoryPercentage: 0.7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 18 } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, stepSize: 1, color: '#64748b', font: { size: 11, weight: '500' } },
                    title: { display: true, text: 'Number of Students', color: '#475569', font: { size: 12, weight: 'bold' } },
                    grid: { color: 'rgba(15, 23, 42, 0.06)' }
                },
                x: {
                    ticks: { color: '#64748b', font: { size: 11, weight: '600' } },
                    title: { display: true, text: 'BITS CGPA Range (Out of 10)', color: '#475569', font: { size: 12, weight: 'bold' } },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', callbacks: { label: function(context) { return `${context.parsed.y} Students`; } } },
                datalabels: { anchor: 'end', align: 'top', offset: 2, color: '#1e293b', font: { weight: 'bold', size: 12 }, formatter: (value) => value > 0 ? value : '' }
            }
        }
    });
}

function updatePerformanceChart() {
    const years = Array.from(document.querySelectorAll('.batch-checkbox:checked')).map(el => el.value);
    const plants = Array.from(document.querySelectorAll('.plant-checkbox:checked')).map(el => el.value);
    const sems = Array.from(document.querySelectorAll('.sem-checkbox:checked')).map(el => el.value);
    // Removed: const streams = ...

    const statusSelect = document.querySelector('select[name="status"]');
    const status = statusSelect ? statusSelect.value : '';

    const payload = {
        year: years,
        plant_location: plants,
        semester: sems,
        // Removed: bits_stream: streams,
        status: status
    };

    fetch('/get-performance-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        initPerformanceChart(data);
    })
    .catch(error => console.error('Error updating performance chart:', error));
}