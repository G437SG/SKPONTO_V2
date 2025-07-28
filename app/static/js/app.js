/**
 * SKPONTO - Sistema de Controle de Ponto
 * JavaScript principal da aplicação
 */

$(document).ready(function() {
    // Request notification permission on page load
    requestNotificationPermission();
    
    // Inicializar tooltips e popovers
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Clock widget
    updateClock();
    setInterval(updateClock, 1000);

    // Check for new notifications every 30 seconds (only if user is authenticated)
    if ($('#notification-count').length > 0) {
        setInterval(checkNotifications, 30000);
        checkNotifications(); // Check immediately
        
        // Also check for daily notifications every minute
        setInterval(checkDailyNotifications, 60000);
    }

    // Load notifications when dropdown is opened
    $('#notificationDropdown').on('show.bs.dropdown', function() {
        loadRecentNotifications();
    });

    // Mark all notifications as read
    $(document).on('click', '#mark-all-read', function(e) {
        e.preventDefault();
        e.stopPropagation();
        markAllNotificationsAsRead();
    });

    // CPF mask
    $('.cpf-mask').on('input', function() {
        let value = this.value.replace(/\D/g, '');
        if (value.length <= 11) {
            value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            this.value = value;
        }
    });

    // Phone mask
    $('.phone-mask').on('input', function() {
        let value = this.value.replace(/\D/g, '');
        if (value.length <= 11) {
            if (value.length <= 10) {
                value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            } else {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            }
            this.value = value;
        }
    });

    // File upload drag and drop
    setupFileUpload();

    // Form validation
    setupFormValidation();

    // Auto-refresh for specific pages
    if (window.location.pathname.includes('/dashboard')) {
        setInterval(function() {
            updateDashboardStats();
        }, 60000); // Update every minute
    }
});

/**
 * Update clock widget
 */
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('pt-BR');
    const dateString = now.toLocaleDateString('pt-BR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    $('#current-time').text(timeString);
    $('#current-date').text(dateString);
}

/**
 * Check for new notifications
 */
function checkNotifications() {
    $.get('/api/notificacoes_nao_lidas')
        .done(function(data) {
            const count = data.count;
            const badge = $('#notification-count');
            
            if (count > 0) {
                badge.text(count).show();
            } else {
                badge.hide();
            }
        })
        .fail(function() {
            console.log('Erro ao buscar notificações');
        });
}

/**
 * Load recent notifications for dropdown
 */
function loadRecentNotifications() {
    const container = $('#recent-notifications');
    
    // Show loading state
    container.html(`
        <li class="dropdown-item-text text-center">
            <i class="fas fa-spinner fa-spin me-2"></i>Carregando...
        </li>
    `);
    
    $.get('/api/notifications/recent')
        .done(function(data) {
            if (data.success && data.notifications.length > 0) {
                let html = '';
                
                data.notifications.forEach(function(notification) {
                    // Truncate message if too long for dropdown
                    let message = notification.mensagem;
                    if (message.length > 80) {
                        message = message.substring(0, 80) + '...';
                    }
                    
                    // Determine icon based on notification type
                    let icon = 'fa-bell';
                    let iconColor = 'text-primary';
                    
                    switch(notification.tipo) {
                        case 'ATESTADO_APROVADO':
                            icon = 'fa-check-circle';
                            iconColor = 'text-success';
                            break;
                        case 'ATESTADO_REJEITADO':
                            icon = 'fa-times-circle';
                            iconColor = 'text-danger';
                            break;
                        case 'PONTO_IRREGULAR':
                            icon = 'fa-exclamation-triangle';
                            iconColor = 'text-warning';
                            break;
                        case 'BACKUP_REALIZADO':
                            icon = 'fa-cloud';
                            iconColor = 'text-info';
                            break;
                        case 'BANCO_HORAS_AJUSTE':
                            icon = 'fa-clock';
                            iconColor = 'text-primary';
                            break;
                    }
                    
                    html += `
                        <li>
                            <a class="dropdown-item notification-item ${!notification.lida ? 'fw-bold' : ''}" 
                               href="/notificacoes" 
                               style="white-space: normal; padding: 10px 16px; border-bottom: 1px solid #f0f0f0;">
                                <div class="d-flex align-items-start">
                                    <div class="me-2 flex-shrink-0">
                                        <i class="fas ${icon} ${iconColor}"></i>
                                    </div>
                                    <div class="flex-grow-1 min-width-0">
                                        <div class="notification-title small ${!notification.lida ? 'fw-bold' : ''}" 
                                             style="line-height: 1.3; margin-bottom: 3px;">
                                            ${notification.titulo}
                                        </div>
                                        <div class="notification-message text-muted small" 
                                             style="line-height: 1.2; word-wrap: break-word; margin-bottom: 3px;">
                                            ${message}
                                        </div>
                                        <div class="notification-time text-muted" style="font-size: 0.75rem;">
                                            <i class="fas fa-clock me-1"></i>${notification.time_ago}
                                        </div>
                                    </div>
                                    ${!notification.lida ? '<div class="flex-shrink-0"><span class="badge bg-primary rounded-pill">Nova</span></div>' : ''}
                                </div>
                            </a>
                        </li>
                    `;
                });
                
                container.html(html);
                
                // Update notification count
                updateNotificationCount(data.unread_count);
                
            } else {
                container.html(`
                    <li class="dropdown-item-text text-center text-muted">
                        <i class="fas fa-inbox me-2"></i>Nenhuma notificação
                    </li>
                `);
                updateNotificationCount(0);
            }
        })
        .fail(function() {
            console.log('Erro ao carregar notificações');
            container.html(`
                <li class="dropdown-item-text text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>Erro ao carregar
                </li>
            `);
        });
}

/**
 * Update notification count badge
 */
function updateNotificationCount(count) {
    const badge = $('#notification-count');
    if (count > 0) {
        badge.text(count).show();
    } else {
        badge.hide();
    }
}

/**
 * Mark all notifications as read
 */
function markAllNotificationsAsRead() {
    $.post('/marcar_todas_lidas', {
        'csrf_token': $('meta[name=csrf-token]').attr('content')
    })
    .done(function() {
        // Reload notifications after marking as read
        loadRecentNotifications();
        showNotification('Todas as notificações foram marcadas como lidas!', 'success');
    })
    .fail(function() {
        showNotification('Erro ao marcar notificações como lidas.', 'error');
    });
}

/**
 * Setup file upload with drag and drop
 */
function setupFileUpload() {
    $('.file-upload-area').on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('dragover');
    });

    $('.file-upload-area').on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
    });

    $('.file-upload-area').on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            const fileInput = $(this).find('input[type="file"]')[0];
            fileInput.files = files;
            $(fileInput).trigger('change');
        }
    });

    // Show selected file name
    $('input[type="file"]').on('change', function() {
        const fileName = this.files[0] ? this.files[0].name : 'Nenhum arquivo selecionado';
        $(this).next('.form-text').text(fileName);
    });
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    // Real-time validation
    $('.needs-validation input').on('blur', function() {
        validateField(this);
    });

    $('.needs-validation form').on('submit', function(e) {
        if (!this.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        this.classList.add('was-validated');
    });
}

/**
 * Validate individual field
 */
function validateField(field) {
    const $field = $(field);
    const value = $field.val();
    
    // CPF validation
    if ($field.hasClass('cpf-validation')) {
        const isValid = validateCPF(value);
        if (!isValid && value.length > 0) {
            $field[0].setCustomValidity('CPF inválido');
        } else {
            $field[0].setCustomValidity('');
        }
    }
    
    // Email validation
    if ($field.attr('type') === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value) && value.length > 0) {
            $field[0].setCustomValidity('Email inválido');
        } else {
            $field[0].setCustomValidity('');
        }
    }
}

/**
 * Validate CPF
 */
function validateCPF(cpf) {
    cpf = cpf.replace(/[^\d]+/g, '');
    
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
        return false;
    }
    
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    
    let remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;
    if (remainder !== parseInt(cpf.charAt(9))) return false;
    
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    
    remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;
    if (remainder !== parseInt(cpf.charAt(10))) return false;
    
    return true;
}

/**
 * Update dashboard statistics
 */
function updateDashboardStats() {
    $.get('/api/estatisticas')
        .done(function(data) {
            // Update notification count
            if (data.notificacoes_nao_lidas > 0) {
                $('#notification-count').text(data.notificacoes_nao_lidas).show();
            } else {
                $('#notification-count').hide();
            }
            
            // Update today's record if exists
            if (data.hoje.entrada) {
                $('.entrada-hoje').text(data.hoje.entrada);
            }
            if (data.hoje.saida) {
                $('.saida-hoje').text(data.hoje.saida);
            }
        })
        .fail(function() {
            console.log('Erro ao atualizar estatísticas');
        });
}

/**
 * Register time (entry/exit)
 */
function registerTime(action) {
    const button = $(`#btn-${action}`);
    const originalText = button.html();
    
    // Show loading
    button.html('<span class="spinner-border spinner-border-sm me-2"></span>Registrando...');
    button.prop('disabled', true);
    
    $.ajax({
        url: '/api/registro_ponto',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': $('meta[name=csrf-token]').attr('content')
        },
        data: JSON.stringify({ acao: action }),
        success: function(response) {
            if (response.success) {
                showNotification(response.message, 'success');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                showNotification(response.message, 'error');
            }
        },
        error: function() {
            showNotification('Erro ao registrar ponto. Tente novamente.', 'error');
        },
        complete: function() {
            button.html(originalText);
            button.prop('disabled', false);
        }
    });
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const alertClass = type === 'error' ? 'danger' : type;
    const icon = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    const toast = $(`
        <div class="alert alert-${alertClass} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            <i class="fas ${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('body').append(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.fadeOut(() => toast.remove());
    }, 5000);
}

/**
 * Confirm action with modal
 */
function confirmAction(title, message, callback) {
    const modalId = 'confirmModal';
    
    // Remove existing modal if any
    $(`#${modalId}`).remove();
    
    const modal = $(`
        <div class="modal fade" id="${modalId}" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${message}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-danger" id="confirmBtn">Confirmar</button>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    $('body').append(modal);
    
    const modalInstance = new bootstrap.Modal(document.getElementById(modalId));
    modalInstance.show();
    
    $('#confirmBtn').on('click', function() {
        callback();
        modalInstance.hide();
    });
    
    // Remove modal from DOM when hidden
    $(`#${modalId}`).on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

/**
 * Format time display
 */
function formatTime(hours) {
    const h = Math.floor(hours);
    const m = Math.floor((hours - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copiado para a área de transferência!', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Copiado para a área de transferência!', 'success');
    }
}

/**
 * Export table to CSV
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    const rows = Array.from(table.querySelectorAll('tr'));
    
    const csvContent = rows.map(row => {
        const cols = Array.from(row.querySelectorAll('td, th'));
        return cols.map(col => `"${col.textContent.trim()}"`).join(',');
    }).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * Request notification permission from user
 */
function requestNotificationPermission() {
    if ("Notification" in window) {
        if (Notification.permission === "default") {
            Notification.requestPermission().then(function(permission) {
                if (permission === "granted") {
                    console.log("Notification permission granted.");
                    // Show welcome notification
                    showDesktopNotification("SKPONTO", "Notificações habilitadas! Você receberá avisos no início e final do dia.");
                } else {
                    console.log("Notification permission denied.");
                }
            });
        }
    } else {
        console.log("This browser does not support desktop notification");
    }
}

/**
 * Show desktop notification
 */
function showDesktopNotification(title, body, icon = null) {
    if ("Notification" in window && Notification.permission === "granted") {
        const notification = new Notification(title, {
            body: body,
            icon: icon || '/static/img/favicon.ico',
            badge: '/static/img/favicon.ico',
            tag: 'skponto-notification'
        });
        
        // Auto close after 5 seconds
        setTimeout(function() {
            notification.close();
        }, 5000);
        
        return notification;
    }
    return null;
}

/**
 * Check if it's time for daily notifications
 */
function checkDailyNotifications() {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    
    // Morning reminder (9:00 AM)
    if (hour === 9 && minute === 0) {
        showDesktopNotification(
            "SKPONTO - Lembrete",
            "Bom dia! Não esqueça de registrar seu ponto de entrada.",
            "/static/img/favicon.ico"
        );
    }
    
    // Evening reminder (17:00 PM)
    if (hour === 17 && minute === 0) {
        showDesktopNotification(
            "SKPONTO - Lembrete",
            "Boa tarde! Não esqueça de registrar seu ponto de saída.",
            "/static/img/favicon.ico"
        );
    }
}

// Global functions for inline use
window.registerTime = registerTime;
window.confirmAction = confirmAction;
window.showNotification = showNotification;
window.requestNotificationPermission = requestNotificationPermission;
window.showDesktopNotification = showDesktopNotification;
window.copyToClipboard = copyToClipboard;
window.exportTableToCSV = exportTableToCSV;
