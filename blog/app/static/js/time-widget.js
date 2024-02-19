
"use strict";


function runTimeWidget() {
	setInterval(() => {
		let date = new Date();
		let hours = date.getHours();
		let minutes = date.getMinutes();
		let seconds = date.getSeconds();

		$('#time-widget').html(`${hours}:${minutes}:${seconds}`);
	}, 1000);
}

$(document).ready(runTimeWidget);
