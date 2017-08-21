
  // Set global flag to avoid multiple calls
  window.loadedFirstTime = true;

  // For IE versions that does'nt support endswith
  if (typeof String.prototype.endsWith !== 'function') {
      String.prototype.endsWith = function(suffix) {
          return this.indexOf(suffix, this.length - suffix.length) !== -1;
      };
  }

  $(document).ajaxSuccess(function(event, xhr, settings){
    if( window.loadedFirstTime == true &&  settings.url.endsWith('course_discovery/') ) {
      var category = decodeURIComponent(getParameterByName('category'));
      window.loadedFirstTime = false;
      if (category !== undefined && category !=null) {
        var $facetButton = $("button[data-value='"+category+"']");
        if($facetButton){
            $facetButton.click();
            // window.history.pushState("", "", '/courses');
        }
      }
    }
  });
