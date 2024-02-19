
"use strict";


function _makeFlashItem(message, category) {
	return `<div class="alert alert-${category} alert-dismissible fade show" role="alert">\
				<strong>Attention!</strong> ${message}\
				<button type="button" class="close" data-dismiss="alert" aria-label="Close">\
					<span aria-hidden="true">&times;</span>\
				</button>\
			</div>`
}


function flash(message, category) {
	let newItem = _makeFlashItem(message, category);
	window.scrollTo({top: 0});
	setTimeout(() => $('#flashes-container').append(newItem), 400);
}
