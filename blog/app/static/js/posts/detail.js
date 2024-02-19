
"use strict";


let infinite = new Waypoint.Infinite({
	element: $('.infinite-container')[0],
});


function onClickReplyButton(commentID) {
	let comment = $(`#comment-${commentID}`);

	$('#reply-info').text(`Reply to ${comment.attr('author-username')}`);
	$('#comment-form').attr('action', comment.attr('reply-url'));
	$('#reply-cancel-btn').css({display: "block"});
}


function onClickReplyCancelButton() {
	$('#reply-info').text('');
	$('#comment-form').attr('action', commentPostURL);
	$('#reply-cancel-btn').css({display: "none"});
}


function onClickCommentDeleteButton(button) {
	if (confirm(messages.areYouSureDeleteComment)) {
		$.ajax({
			url: button.getAttribute('delete-url'),
			type: 'POST', data: {csrf_token: csrfToken},
			success: () => {
				flash(messages.commentDeletedSuccess, 'danger');

				let commentID = button.getAttribute('comment-id');
				$(`#comment-${commentID}`).remove();
				$(`.comment-${commentID}-child`).remove();
			},
		});
	}
}
