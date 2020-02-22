let timer, decInterval, reqInterval;

function left_pad(string, pad, length) { // NOTE: Does not work with decimals ('001.23'.slice(-2) is 23 instead of 01)
    var res = (new Array(length+1).join(pad)+string).slice(-length);
    //console.log(string,pad,length, '=>', res);
    return res;
    
}

function formatTime(secs) {
    secs = Math.round(secs); // weird string slice behavior with decimals
    var neg = false;
    if (secs < 0) {
        neg = true;
    }
    secs = Math.abs(secs);
    var m = Math.floor(secs / 60);
    var s = secs - (m * 60);
    //console.log('format result: ', secs, m.toString() + ':' + s.toString(), res);
    return (neg ? '-':'') + left_pad(m,'0',2)+':'+left_pad(s,'0',2);
}

function updateTime(t) { /* Update the time display */
    s = formatTime(t);
    $('#time').text(s);
} 


function getstatus() {
    $("#loading").show();
    $.getJSON('/api/status') 
        .done(function (data) {
            $("#loading").hide();
            //console.log('Status text: ', data);
            if (data.remaining === undefined || data.running === undefined) {
                return error('status', data);
            }
            status = data.running ? "Running" : "Paused";
            $('#msg').text('Timer status: ' + status);
            console.log("data: ", data, "\nstatus: " + status);
            window.timer = data;
            if (data.clients) {
                $("#connected-clients").html(data.clients.join("<br>"));
            }
            updateTime(window.timer.remaining);
            return data;
        })
        .fail(function (data) {
            $("#loading").hide();
            error('status', data);
            timer = null;
            return null;
        });
}

function dec() {
    if (window.timer && window.timer.running) {
        window.timer.remaining--;
        updateTime(window.timer.remaining);
    }
}

function error(name, data) {
    //alert(name + ' failed! ' + 'Status: ' + data.status + '\nMessage: ' + data.responseText);
    if (data.error) {
        alert("Error: " + data.error);
    }
    alert("Couldn't reach the server. Check your connection and reload");
    clearInterval(decInterval);
    clearInterval(reqInterval);
    console.warn('[REQUEST ERROR]' + name + ' failed ', data);
}

function load_time_pref() {
    pref = parseInt(localStorage.getItem('timePref'));
    if (pref === null || isNaN(pref)) {
        pref = 0;
    }
    console.log('Loaded time preference as ' + pref);
    secs = Math.round(pref); // weird string slice behavior with decimals
    var m = Math.floor(secs / 60);
    var s = left_pad((secs - (m * 60)),'0',2);
    $('#min').val(m);
    $('#sec').val(s);
}

$('#start-btn').click(function start() {
    $.post('/api/start')
        .done(function (data) {
            if (data.error) {
                return alert("Error: " + data.error);
            }
            console.log('[REQUEST] /api/start success ', data);
            getstatus(); // instant update
        })
        .fail(function (data) {
            error('/api/start', data);
        });
});

$('#stop-btn').click(function stop() {
    $.post('/api/stop')
        .done(function (data) {
            if (data.error) {
                return alert("Error: " + data.error);
            }
            console.log('[REQUEST] /api/stop success ', data);
            getstatus(); // instant update
        })
        .fail(function (data) {
            error('/api/stop', data);
        });
});

$('#set-btn').click(function () {
    min = parseInt($('#min').val());
    sec = parseInt($('#sec').val());
    if (isNaN(min)) {
        alert('Please enter a valid number of minutes');
        return;
    } else if (isNaN(sec)) {
        alert('Please enter a valid number of seconds');
        return;
    }
    var time = (min * 60) + sec;
    console.log('Set time pref as ' + time);
    localStorage.setItem('timePref', time);
    $.post('/api/set', {'sec': time})
        .done(function(data) {
            if (data.error) {
                return alert("Error: " + data.error);
            }
            console.log('[REQUEST] /api/set success ', data);
            getstatus(); // instant update
        })
        .fail(function(data) {
            if (data.status == 400 && data.responseText) {
                alert("Error from server: " + data.repsonseText);
            }
            error('/api/set', data);
        });
});

$(document).ready(function ready() {
    console.log('Ready. ');
    load_time_pref();
    getstatus();
    $('#start-btn').attr('disabled', false);
    $('#stop-btn').attr('disabled', false);
    $('#set-btn').attr('disabled', false);
    reqInterval = setInterval(getstatus, 3000);
    decInterval = setInterval(dec, 1000);
});
