$('document').ready(function(){
   // home page login boxes
   $( "#login-btn" ).click(function() {
     $( "#login-form" ).submit();
   });

   // hide / show feed page new tweet box
   $( "textarea#new-tweet" ).focusin(function() {
      $(this).attr("rows", "3");
      $(".tweet-submit").show();
   });
   $( "textarea#new-tweet" ).focusout(function() {
      if ( !$(this).val() ) {
         $(this).attr("rows", "1");
         $(".tweet-submit").hide();
      }
   });
   $('textarea#new-tweet').bind('input propertychange', function() {
      $(".char-count").html(140 - $("textarea#new-tweet").val().length);
   });
});



