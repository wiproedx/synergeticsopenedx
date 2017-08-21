$(document).ready(function(){   
    var userInterface = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var newData = new FormData();
        newData.append('logo', $("#upload_logo").prop('files')[0]);
        newData.append('favicon', $("#upload_favicon").prop('files')[0]);
        newData.append('site-color', $("#site-color").val());
        newData.append('template-id', $('input[name=template-id]:checked').val());
        newData.append('save-change-id', linkID);
        fireAjax(newData, linkID)
    };

    var staticContent = function(){
        if($("#static_page_content")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var page = $("#heard option:selected").val();
            if (page == ''){ return }
            var newData = new FormData();
            var content = $("#page-content").html()
            newData.append('page', page)
            newData.append('content', content)
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
            $("#static_page_content").validator('validate')
        }
    }

    var createUser = function(){
        if($("#new-user")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var newData = new FormData();
            newData.append('email', $("#email").val())
            newData.append('name', $("#name").val())
            newData.append('username', $("#username").val())
            newData.append('password', $("#password").val())
            newData.append('state', $("#state").val())
            newData.append('admin', $("#admin").parent().hasClass("checked"))
            newData.append('instructor', $("#instructor").parent().hasClass("checked"))
            newData.append('site_admin', $("#site_admin").parent().hasClass("checked"))
            newData.append('mail_credentials', $("#mail_credentials").parent().hasClass("checked"))
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
            $("#new-user").validator('validate')
        }
    }

    var deleteUser = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var userId = this.dataset.userid
        var newData = new FormData();
        newData.append('user_id', userId)
        newData.append('save-change-id', linkID)
        fireAjax(newData, linkID)
    }

    var deleteCourse = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var courseKey = this.dataset.coursekey
        var newData = new FormData();
        newData.append('course_id', courseKey)
        newData.append('save-change-id', linkID)
        fireAjax(newData, linkID)
    }

    var deleteProgram = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var program_id = this.dataset.coursekey
        var newData = new FormData();
        newData.append('program_id', program_id)
        newData.append('save-change-id', linkID)
        fireAjax(newData, linkID)
    }

    var createCoupon = function(){
        if($("#new-coupon")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var newData = new FormData();
            newData.append('code', $("#code").val())
            newData.append('description', $("#description").val())
            newData.append('course_id', $("#course_id").val())
            newData.append('discount', $("#discount").val())
            newData.append('expiration_date', $("input[name=expiration_date]").val())
            newData.append('active', $("#active").parent().hasClass("checked"))
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
            $('#new-coupon').validator('validate')
        }
    }

    var updateCoupon = function(){
        if($("#coupon-details")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var newData = new FormData();
            newData.append('coupon_id', $("#coupon_id").val())
            newData.append('code', $("#code").val())
            newData.append('description', $("#description").val())
            newData.append('course_id', $("#course_id").val())
            newData.append('discount', $("#discount").val())
            newData.append('expiration_date', $("input[name=expiration_date]").val())
            newData.append('active', $("#active").parent().hasClass("checked"))
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
           $("#coupon-details").validator('validate') 
        }
    }

    var deleteCoupon = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var courseId = this.dataset.couponid
        var newData = new FormData();
        newData.append('coupon_id', courseId)
        newData.append('save-change-id', linkID)
        fireAjax(newData, linkID)
    }

    var createProgramCoupon = function(){
        if($("#new-program-coupon")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var newData = new FormData();
            newData.append('code', $("#code").val())
            newData.append('description', $("#description").val())
            newData.append('program_id', $("#program_id").val())
            newData.append('discount', $("#discount").val())
            newData.append('expiration_date', $("input[name=expiration_date]").val())
            newData.append('active', $("#active").parent().hasClass("checked"))
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
            $('#new-program-coupon').validator('validate')
        }
    }

    var updateProgramCoupon = function(){
        if($("#program-coupon-details")[0].checkValidity()){
            this.setAttribute("disabled", true);
            var linkID = this.id
            var newData = new FormData();
            newData.append('coupon_id', $("#coupon_id").val())
            newData.append('code', $("#code").val())
            newData.append('description', $("#description").val())
            newData.append('program_id', $("#program_id").val())
            newData.append('discount', $("#discount").val())
            newData.append('expiration_date', $("input[name=expiration_date]").val())
            newData.append('active', $("#active").parent().hasClass("checked"))
            newData.append('save-change-id', linkID)
            fireAjax(newData, linkID)
        }else{
           $("#program-coupon-details").validator('validate') 
        }
    }

    var deleteProgramCoupon = function(){
        this.setAttribute("disabled", true);
        var linkID = this.id
        var courseId = this.dataset.couponid
        var newData = new FormData();
        newData.append('coupon_id', courseId)
        newData.append('save-change-id', linkID)
        fireAjax(newData, linkID)
    }

    var fireAjax = function(data, id){
        var url = getUrl(id);
        data.append('csrfmiddlewaretoken', getCookie('csrftoken'))
        $.post({
            type: "POST",
            url: url,
            cache: false,
            processData: false,
            contentType: false,
            data: data,
            success: function(response, data){
                window.location.reload()
            },
            error: function(error){
                displayError(error)
            }
        })
    };

    var displayError = function(error){
        mainDiv = error.responseJSON.divId;
        error_message = error.responseJSON.errorMsg;
        error_class = "#"+mainDiv+" .error"
        error_message_class = error_class + " .message"
        saveChangeButtonId = error.responseJSON.saveChangeId
        if ($(error_class).hasClass("hidden")){
            $(error_class).removeClass("hidden")
        }
        $(error_message_class).html(error_message)
        $("#"+saveChangeButtonId).removeAttr("disabled")
    };

    var getCookie = function(name){
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var getUrl = function(urlfor){
        urlDictionary = {'user-interface': '/site-administration/save-site-details/',
                         'static-pages': '/site-administration/add_static_content/',
                         'confirm-delete-user': '/site-administration/delete-user/',
                         'create-user': '/site-administration/create-user/',
                         'confirm-delete-course': '/site-administration/delete-course/',
                         'confirm-delete-program': '/site-administration/delete-program/',
                         'create-coupon': '/site-administration/new-coupon/',
                         'update-coupon': '/site-administration/update-coupon/',
                         'confirm-delete-coupon': '/site-administration/delete-coupon/',
                         'create-program-coupon': '/site-administration/new-program-coupon/',
                         'update-program-coupon': '/site-administration/update-program-coupon/',
                         'confirm-delete-program-coupon': '/site-administration/delete-program-coupon/'}
        return urlDictionary[urlfor]
    };

    $('#user-interface').bind('click', userInterface);
    $("#static-pages").bind('click', staticContent);
    $("#create-user").bind('click', createUser);
    $("#confirm-delete-user").bind('click', deleteUser);
    $("#confirm-delete-course").bind('click', deleteCourse);
    $("#confirm-delete-program").bind('click', deleteProgram);
    $("#create-coupon").bind('click', createCoupon)
    $("#confirm-delete-coupon").bind('click', deleteCoupon);
    $("#update-coupon").bind('click', updateCoupon);
    $("#create-program-coupon").bind('click', createProgramCoupon)
    $("#update-program-coupon").bind('click', updateProgramCoupon)
    $("#confirm-delete-program-coupon").bind('click', deleteProgramCoupon)
});
