	/* jshint esversion: 11, esnext: false */
	// Section navigation
	function showSection(sectionId) {
		// Hide all sections
		document.querySelectorAll(".section-content").forEach((section) => {
			section.style.display = "none";
		});

		// Remove active class from all menu items
		document.querySelectorAll(".menu-item").forEach((item) => {
			item.classList.remove("active");
		});

		// Show selected section
		document.getElementById(sectionId).style.display = "block";

		// Add active class to clicked menu item
		event.target.closest(".menu-item").classList.add("active");

		// Update URL hash
		window.location.hash = sectionId;
	}

	// Handle page load with hash
	document.addEventListener("DOMContentLoaded", function () {
		const hash = window.location.hash.substring(1);
		if (hash && document.getElementById(hash)) {
			showSection(hash);
		}
	});

	// Account deletion confirmation
	function confirmDeletion() {
		const confirmText = document.querySelector('input[name="deletion_confirm"]').value;
		const password = document.querySelector('input[name="password_confirm"]').value;

		if (confirmText !== "DELETE MY ACCOUNT") {
			alert('Please type "DELETE MY ACCOUNT" exactly as shown to confirm deletion.');
			return false;
		}

		if (!password) {
			alert("Please enter your password to confirm deletion.");
			return false;
		}

		return confirm("This is your final warning!\n\n" + "Are you absolutely sure you want to delete your account?\n" + "This action cannot be undone and all your data will be lost forever.\n\n" + "Click OK to proceed with deletion, or Cancel to keep your account.");
	}

	// Profile picture preview
	function previewImage(input) {
		if (input.files && input.files[0]) {
			const reader = new FileReader();
			reader.onload = function (e) {
				document.getElementById("current-avatar").src = e.target.result;
			};
			reader.readAsDataURL(input.files[0]);
		}
	}

	// Remove profile picture
	function removeProfilePicture() {
		if (confirm("Are you sure you want to remove your profile picture?")) {
			document.getElementById("remove-picture-form").submit();
		}
	}