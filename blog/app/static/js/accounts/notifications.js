
"use strict";


function onClickCheckNotificationButton(button) {
	$.ajax({url: button.getAttribute("check-url"),
			type: 'POST', data: {csrf_token: csrfToken},
			success: () => button.remove()});
}
