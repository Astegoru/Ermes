function getAccessToken() {
  return localStorage.getItem("accessToken");
}

function clearAuthTokens() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}

async function logout(redirectPath = "/login") {
  const token = getAccessToken();
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: token ? { "Authorization": `Bearer ${token}` } : {}
    });
  } catch (_error) {
    // Keep client-side logout resilient even if network fails.
  }
  clearAuthTokens();
  window.location.href = redirectPath;
}

function attachLogout(buttonId, redirectPath = "/login") {
  const button = document.getElementById(buttonId);
  if (!button) {
    return;
  }

  button.addEventListener("click", (event) => {
    event.preventDefault();
    logout(redirectPath);
  });
}

function redirectIfUnauthorized(response, loginPath = "/login") {
  if (response.status !== 401) {
    return false;
  }

  clearAuthTokens();
  window.location.href = loginPath;
  return true;
}
