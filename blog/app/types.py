from typing import Optional, TypedDict


class LoginTwoFactorTypedDict(TypedDict):
	user_id: int
	next_url: Optional[str]
