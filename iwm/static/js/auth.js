function showAlertAndRedirect(message, redirectUrl) {
  alert(message);
  setTimeout(function() {
      window.location.href = redirectUrl;
  }, 0);
}
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".full-input input").forEach((input) => {
    if (input.value.trim() !== "") {input.parentElement.classList.add("filled");} else {input.parentElement.classList.remove("filled");}
    input.addEventListener("input", function () {
      if (this.value.trim() !== "") {
        this.parentElement.classList.add("filled");
      } else {
        this.parentElement.classList.remove("filled");
      }
    });
  });
 // ---- Validation Functions ----
function validateUser(user) {
    user = user.trim();
    if (user.length < 3 || user.length > 20) {
        return false;
    }
    if (/\s/.test(user)) {
        return false;
    }
    const regex = /^[a-zA-Z0-9_-]+$/;
    return regex.test(user);
}


  function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function validatePassword(password) {
    return /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/.test(password);
  }

  // ---- Toggle Password Visibility ----
  function togglePassword(eyeButton, input) {
    if (input.type === "password") {
      input.type = "text";
      eyeButton.querySelector(".open").style.display = "none";
      eyeButton.querySelector(".close").style.display = "inline";
    } else {
      input.type = "password";
      eyeButton.querySelector(".open").style.display = "inline";
      eyeButton.querySelector(".close").style.display = "none";
    }
  }

  // ---- Setup Validation That Fires on Every Input ----
  function setupValidation(input, errorElement, validateFn, errorMsg) {
    input.addEventListener("input", function () {
      if (!validateFn(input.value)) {
        errorElement.textContent = errorMsg;
      } else {
        errorElement.textContent = "";
      }
    });
    // Optional: forceValidate for use on form submit
    return function forceValidate() {
      if (!validateFn(input.value)) {
        errorElement.textContent = errorMsg;
        return false;
      } else {
        errorElement.textContent = "";
        return true;
      }
    };
  }

  // ---- Login Form Handling ----
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    const loginEmailInput = document.getElementById("login-email");
    const loginPasswordInput = document.getElementById("login-password");
    const loginEmailError = document.getElementById("login-emailError");
    const loginPasswordError = document.getElementById("login-passwordError");
    const loginEyeButton = document.getElementById("login-eye-button");
    const loginSubmitButton = loginForm.querySelector('button[type="submit"]');

    const forceValidateEmail = setupValidation(
      loginEmailInput,
      loginEmailError,
      validateEmail,
      "Invalid email format"
    );
    const forceValidatePassword = setupValidation(
      loginPasswordInput,
      loginPasswordError,
      validatePassword,
      "Password must be 8+ chars, 1 uppercase, 1 lowercase, 1 number, 1 special character."
    );

    // CapsLock warning on login password input
    loginPasswordInput.addEventListener("keyup", function (e) {
      if (e.getModifierState("CapsLock")) {
        loginPasswordError.textContent = "Warning: Caps Lock is ON!";
      } else {
        if (!validatePassword(loginPasswordInput.value)) {
          loginPasswordError.textContent =
            "Password must be 8+ chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.";
        } else {
          loginPasswordError.textContent = "";
        }
      }
    });

    if (loginEyeButton) {
      loginEyeButton.addEventListener("click", function () {
        togglePassword(loginEyeButton, loginPasswordInput);
      });
    }

    loginForm.addEventListener("submit", function (e) {
      const validEmail = forceValidateEmail();
      const validPassword = forceValidatePassword();
      if (!validEmail || !validPassword) {
        e.preventDefault();
      } else {
        loginSubmitButton.textContent = "Processing...";
        loginSubmitButton.disabled = true;
        setTimeout(() => {
          loginSubmitButton.textContent = "Submit";
          loginSubmitButton.disabled = false;
          alert("Login form submitted successfully!");
        }, 1500);
      }
    });
  }

  // ---- Signup Form Handling ----
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    const signupEmailInput = document.getElementById("signup-email");
    const signupPasswordInput = document.getElementById("signup-password");
    const signupConfirmPasswordInput = document.getElementById("signup-confirm-password");
    const signupUsernameInput = document.getElementById("signup-username"); // Make sure your HTML has this element

    const signupEmailError = document.getElementById("signup-emailError");
    const signupPasswordError = document.getElementById("signup-passwordError");
    const signupConfirmPasswordError = document.getElementById("signup-confirm-password-error");
    const signupUserError = document.getElementById("user-error");

    const signupEyeButton = document.getElementById("signup-eye-button");
    const signupEyeButtonC = document.getElementById("signup-eye-buttonc");
    const signupSubmitButton = signupForm.querySelector('button[type="submit"]');

    const forceValidateUser = setupValidation(
      signupUsernameInput,
      signupUserError,
      validateUser,
      "Username must be a single part, alphanumeric, and between 3 and 20 characters long, with no spaces."
    );
    const forceValidateEmail = setupValidation(
      signupEmailInput,
      signupEmailError,
      validateEmail,
      "Invalid email format"
    );
    const forceValidatePassword = setupValidation(
      signupPasswordInput,
      signupPasswordError,
      validatePassword,
      "Password must be 8+ chars, 1 uppercase, 1 lowercase, 1 number, 1 special character."
    );

    // Confirm password: validate on every input
    signupConfirmPasswordInput.addEventListener("input", function () {
      if (signupPasswordInput.value !== signupConfirmPasswordInput.value) {
        signupConfirmPasswordError.textContent = "Passwords do not match";
      } else {
        signupConfirmPasswordError.textContent = "";
      }
    });
    function forceValidateConfirm() {
      if (signupPasswordInput.value !== signupConfirmPasswordInput.value) {
        signupConfirmPasswordError.textContent = "Passwords do not match";
        return false;
      } else {
        signupConfirmPasswordError.textContent = "";
        return true;
      }
    }

    // CapsLock warning on signup password input
    signupPasswordInput.addEventListener("keyup", function (e) {
      if (e.getModifierState("CapsLock")) {
        signupPasswordError.textContent = "Warning: Caps Lock is ON!";
      } else {
        if (!validatePassword(signupPasswordInput.value)) {
          signupPasswordError.textContent =
            "Password must be 8+ chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.";
        } else {
          signupPasswordError.textContent = "";
        }
      }
    });

    if (signupEyeButton) {
      signupEyeButton.addEventListener("click", function () {
        togglePassword(signupEyeButton, signupPasswordInput);
      });
    }
    if (signupEyeButtonC) {
      signupEyeButtonC.addEventListener("click", function () {
        togglePassword(signupEyeButtonC, signupConfirmPasswordInput);
      });
    }

    signupForm.addEventListener("submit", function (e) {
      const validUser = forceValidateUser();
      const validEmail = forceValidateEmail();
      const validPassword = forceValidatePassword();
      const validConfirm = forceValidateConfirm();
      if (!validUser || !validEmail || !validPassword || !validConfirm) {
        e.preventDefault();
        alert("Error: Please fix the highlighted fields before submitting.");
      } else {
        signupSubmitButton.textContent = "Processing...";
        signupSubmitButton.disabled = true;
        setTimeout(() => {
          signupSubmitButton.textContent = "Submit";
          signupSubmitButton.disabled = false;
          alert("Signup form submitted successfully!");
        }, 500);
      }
    });
  }
});