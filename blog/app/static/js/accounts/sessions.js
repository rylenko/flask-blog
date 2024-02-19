
function onClickSessionTerminateButton(button) {
	if (confirm(messages.areYouSureTerminateSession)) {
		$.ajax({
			url: button.getAttribute('terminate-url'),
			type: 'POST', data: {csrf_token: csrfToken},
			success: () => {
				flash(messages.sessionTerminatedSuccess, 'danger');
				let sessionID = button.getAttribute('session-id');
				$(`#session-${sessionID}`).remove();
			},
		});
	}
}
