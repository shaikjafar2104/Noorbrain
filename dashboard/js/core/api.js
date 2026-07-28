(() => {
  "use strict";

  const API = window.location.origin;

  async function request(path, options = {}) {
    const response = await fetch(
      API + path,
      {
        cache: "no-store",
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {})
        }
      }
    );

    if (!response.ok) {
      const message = await response.text();

      throw new Error(
        `${response.status} ${message}`
      );
    }

    const contentType =
      response.headers.get("content-type") || "";

    if (
      response.status === 204 ||
      !contentType.includes("application/json")
    ) {
      return {};
    }

    return response.json();
  }

  window.NoorAPI = {
    base: API,
    request
  };
})();
