
"use strict";


document.cookie = "foo=bar;";
if (!document.cookie) {
	alert("This website requires cookies to function properly.");
}


function runNotCheckedNotificationsWidget(fetchCountURL) {
	const widgetPlace = '#not-checked-notifications-count';

	setInterval(() => {
		$.ajax({url: fetchCountURL, type: 'GET',
				success: data => $(widgetPlace).text(data.not_checked)});
	}, 5000);
}
