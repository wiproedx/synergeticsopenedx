$(document).ready(function(){
    $(".field-update").on('change', function(){
        $("#student_details").addClass("blur-background")
        $(".ajax-loader").removeClass("hidden")
        var type = this.type
        var name = this.name
        // if(type=='checkbox'){value=this.checked}else{value=this.value}
        var value = (type=='checkbox') ? this.checked : this.value
        var user_id = $("#user_id").val()
        var data = {'type': type, 'name': name, 'value': value, 'user_id': user_id}
        update_user(data);
    });
    var update_user = function(data){
        $.ajax({
            type: "POST",
            url: "/site-administration/update-user/",
            data: data,
            success: function(data){
                $(".ajax-loader").addClass("hidden")
                $("#student_details").removeClass("blur-background")
                $("#alert").removeClass("hidden");
                $("#alert").addClass("alert-success");
                $("#alert").empty()
                $("#alert").append("<p><strong>"+ data.message +"</strong></p>")
            },
            error: function(e){
                $(".ajax-loader").addClass("hidden")
                $("#student_details").removeClass("blur-background")
                $("#alert").removeClass("hidden");
                $("#alert").addClass("alert-danger");
                $("#alert").empty()
                $("#alert").append("<p><strong>"+ e.message +"</strong></p>")
            }
        });
    }
});